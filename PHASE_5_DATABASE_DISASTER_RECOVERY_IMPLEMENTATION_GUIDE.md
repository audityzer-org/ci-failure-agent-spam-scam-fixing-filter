# Phase 5: Database & Disaster Recovery Implementation Guide

## Overview
This phase establishes production-grade database infrastructure with comprehensive disaster recovery (DR) capabilities, backup strategies, and failover mechanisms.

## Database Architecture

### PostgreSQL Cluster Setup
```yaml
PostgreSQL HA Configuration:
- Primary-Replica replication
- Streaming replication with WAL archiving
- Point-in-time recovery (PITR)
- Automated failover with Patroni
- Read replicas for analytics workloads
```

### Implementation Steps

#### 1. Install PostgreSQL with Patroni
```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Install PostgreSQL and Patroni
sudo apt update
sudo apt install -y postgresql-14 postgresql-contrib-14
pip install patroni[kubernetes]

# Create Patroni configuration
sudo mkdir -p /etc/patroni
sudo tee /etc/patroni/patroni.yml > /dev/null <<EOF
scope: ci-failure-agent-db
namespace: /service
name: postgres-primary

restapi:
  listen: 0.0.0.0:8008
  connect_address: 192.168.1.10:8008

etcd:
  host: etcd-cluster:2379

postgresql:
  data_dir: /var/lib/postgresql/14/main
  bin_dir: /usr/lib/postgresql/14/bin
  listen: 0.0.0.0:5432
  connect_address: 192.168.1.10:5432
  
  parameters:
    shared_buffers: 256MB
    effective_cache_size: 1GB
    maintenance_work_mem: 64MB
    random_page_cost: 1.1
    wal_level: replica
    max_wal_senders: 10
    max_replication_slots: 10
    hot_standby: 'on'
    wal_keep_size: 1GB
    archive_mode: 'on'
    archive_command: 'test ! -f /backup/wal_archive/%f && cp %p /backup/wal_archive/%f'
EOF

# Start Patroni
sudo systemctl enable patroni
sudo systemctl start patroni
```

#### 2. Configure WAL Archiving
```bash
# Create WAL archive directory
sudo mkdir -p /backup/wal_archive
sudo chown postgres:postgres /backup/wal_archive
sudo chmod 700 /backup/wal_archive

# Configure S3 archiving (optional)
pip install pgbackrest

sudo tee /etc/pgbackrest/pgbackrest.conf > /dev/null <<EOF
[global]
repo1-path=/var/lib/pgbackrest
repo1-s3-bucket=ci-failure-agent-backup
repo1-s3-region=us-east-1
repo1-type=s3
repo1-retention-full=7
process-max=4
log-level-console=info
log-level-file=debug

[stanza-db]
db-path=/var/lib/postgresql/14/main
db-port=5432
EOF

sudo chmod 640 /etc/pgbackrest/pgbackrest.conf
sudo chown postgres:postgres /etc/pgbackrest/pgbackrest.conf
```

## Backup Strategy

### Full Backup Schedule
```yaml
Backup Policy:
  Full Backups: Daily at 02:00 UTC
  Incremental: Every 4 hours
  Retention: 7 days for full, 2 days for incremental
  WAL Archive: Continuous with 1GB retention
  Encryption: AES-256 for S3 storage
  Compression: LZ4 compression enabled
```

### pgBackRest Configuration
```bash
# Initialize pgBackRest stanza
sudo -u postgres pgbackrest --stanza=db-stanza stanza-create

# Create initial backup
sudo -u postgres pgbackrest --stanza=db-stanza backup

# Verify backup
sudo -u postgres pgbackrest --stanza=db-stanza info
```

## Disaster Recovery Procedures

### Point-in-Time Recovery (PITR)
```bash
# Restore to specific timestamp
cd /var/lib/postgresql/14/main
sudo -u postgres pg_basebackup -h 192.168.1.10 -D /var/lib/postgresql/14/main -P -v -W -R

# Create recovery.conf
sudo tee /var/lib/postgresql/14/main/recovery.conf > /dev/null <<EOF
restore_command = 'pgbackrest --stanza=db-stanza archive-get %f \"%p\"'
recovery_target_timeline = latest
recovery_target_xid = '1234567890'
recovery_target_inclusive = true
pause_at_recovery_target = false
EOF

# Start PostgreSQL
sudo systemctl start postgresql
```

### Automated Failover with Patroni
```bash
# Monitor cluster status
patronictl -c /etc/patroni/patroni.yml list

# Manual switchover (if needed)
patronictl -c /etc/patroni/patroni.yml switchover

# View failover history
patronictl -c /etc/patroni/patroni.yml history
```

## Read Replica Configuration

### Kubernetes-based Read Replicas
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-read-replica-config
  namespace: ci-failure-agent
data:
  postgresql.conf: |
    # Read replica settings
    hot_standby = on
    max_standby_streaming_delay = 300s
    wal_receiver_status_interval = 10s
    hot_standby_feedback = on
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres-read-replica
  namespace: ci-failure-agent
spec:
  serviceName: postgres-read-replica
  replicas: 2
  selector:
    matchLabels:
      app: postgres-read-replica
  template:
    metadata:
      labels:
        app: postgres-read-replica
    spec:
      containers:
      - name: postgres
        image: postgres:14-alpine
        ports:
        - containerPort: 5432
        env:
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        - name: POSTGRES_REPLICATION_MODE
          value: "slave"
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        - name: postgres-config
          mountPath: /etc/postgresql
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 100Gi
```

## Backup Verification

### Automated Backup Tests
```bash
#!/bin/bash
# backup-verification.sh

set -e

STANZA="db-stanza"
TEST_DIR="/tmp/pgbackrest-test"

echo "Starting backup verification..."

# List recent backups
echo "Recent backups:"
pgbackrest --stanza=$STANZA info

# Test restore in isolated environment
echo "Testing restore..."
mkdir -p $TEST_DIR
cd $TEST_DIR

pgbackrest --stanza=$STANZA restore \
  --delta \
  --repo=1

# Verify restored data
if [ -f "PG_VERSION" ]; then
    echo "✓ Backup verification successful"
    rm -rf $TEST_DIR
    exit 0
else
    echo "✗ Backup verification failed"
    exit 1
fi
```

## Monitoring & Alerting

### Prometheus Metrics
```yaml
# Queries for monitoring
- alert: PostgreSQLReplicationLag
  expr: pg_replication_lag_bytes > 1073741824
  for: 5m
  annotations:
    summary: "PostgreSQL replication lag > 1GB"

- alert: PostgreSQLBackupAge
  expr: (time() - pg_backup_timestamp) > 86400
  for: 1h
  annotations:
    summary: "PostgreSQL backup is older than 24 hours"

- alert: PostgreSQLWALArchiveFailure
  expr: pg_wal_archive_failed_count > 0
  for: 5m
  annotations:
    summary: "PostgreSQL WAL archiving failures detected"
```

## Database Maintenance

### Vacuum & Analyze Schedule
```bash
# Add to crontab
0 3 * * * sudo -u postgres /usr/lib/postgresql/14/bin/vacuumdb -U postgres -d ci_failure_agent -z
0 4 * * * sudo -u postgres /usr/lib/postgresql/14/bin/reindexdb -U postgres -d ci_failure_agent
```

## Deliverables

✓ PostgreSQL HA cluster with Patroni
✓ WAL archiving with pgBackRest
✓ Point-in-time recovery configuration
✓ Read replica setup
✓ Automated backup verification
✓ Disaster recovery runbooks
✓ Monitoring and alerting rules
✓ Database maintenance scripts

## Next Steps

Phase 6: ML Infrastructure Preparation
- Feature store implementation
- Model serving infrastructure
- Experiment tracking
- Data pipeline orchestration

Phase 6.1: Q1 2026 ML Setup
- Start Q1 2026 machine learning infrastructure
