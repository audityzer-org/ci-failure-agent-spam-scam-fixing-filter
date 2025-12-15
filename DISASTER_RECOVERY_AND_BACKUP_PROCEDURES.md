# Disaster Recovery and Backup Procedures

## Overview
This document defines comprehensive disaster recovery (DR) and backup procedures for the Audityzer production infrastructure to ensure business continuity and rapid recovery from catastrophic failures.

## Table of Contents
1. [Recovery Objectives](#recovery-objectives)
2. [Backup Strategy](#backup-strategy)
3. [Disaster Recovery Plan](#disaster-recovery-plan)
4. [Failover Procedures](#failover-procedures)
5. [Testing and Validation](#testing-and-validation)
6. [Runbooks](#runbooks)

## Recovery Objectives

### RTO and RPO
```
Service Component          RTO (Recovery Time)    RPO (Recovery Point)
===============================================================================
Primary API Service        5 minutes              5 minutes
Database (RDS)            15 minutes             5 minutes (continuous)
Cache Layer (Redis)       5 minutes              Re-warm required
Storage (S3)              30 minutes             None (versioning)
CI/CD Pipeline            30 minutes             None (git-based)
Monitoring Stack          1 hour                 24 hours
```

### SLA Commitments
- **Primary Services**: 99.95% uptime
- **Non-critical Services**: 99.0% uptime
- **Data Loss**: <5 minutes
- **Service Recovery**: <15 minutes

## Backup Strategy

### Database Backups
```hcl
# Automated RDS Backup Configuration
resource "aws_db_instance" "backup_config" {
  # Continuous backups
  backup_retention_period = 30  # days
  backup_window          = "03:00-04:00"
  copy_tags_to_snapshot  = true
  
  # Enable automated backups
  skip_final_snapshot = false
  final_snapshot_identifier = "audityzer-final-snapshot-${timestamp()}"
  
  # Enhanced monitoring
  enable_cloudwatch_logs_exports = [
    "postgresql"
  ]
}

# Cross-region backup replication
resource "aws_db_instance_automated_backups_replication" "replica" {
  source_db_instance_arn = aws_db_instance.main.arn
  backup_retention_period = 30
}
```

### Application State Backups
```bash
#!/bin/bash
# Backup application state to S3

set -e

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BUCKET="audityzer-backups"
REGION="eu-west-1"

echo "[1] Creating etcd snapshot..."
kubectl exec -n kube-system etcd-master -- \
  etcdctl snapshot save /tmp/etcd-snapshot-${BACKUP_DATE}.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

echo "[2] Backing up ConfigMaps and Secrets..."
kubectl get configmaps --all-namespaces -o yaml > /tmp/configmaps-${BACKUP_DATE}.yaml
kubectl get secrets --all-namespaces -o yaml > /tmp/secrets-${BACKUP_DATE}.yaml

echo "[3] Uploading to S3..."
aws s3 cp /tmp/etcd-snapshot-${BACKUP_DATE}.db s3://${BUCKET}/backups/ --region ${REGION}
aws s3 cp /tmp/configmaps-${BACKUP_DATE}.yaml s3://${BUCKET}/backups/ --region ${REGION}
aws s3 cp /tmp/secrets-${BACKUP_DATE}.yaml s3://${BUCKET}/backups/ --region ${REGION}

echo "[4] Cleanup local files..."
rm /tmp/etcd-snapshot-${BACKUP_DATE}.db
rm /tmp/configmaps-${BACKUP_DATE}.yaml
rm /tmp/secrets-${BACKUP_DATE}.yaml

echo "Backup completed successfully at $(date)"
```

### S3 Backup Configuration
```hcl
# S3 Backup Bucket
resource "aws_s3_bucket" "backups" {
  bucket = "audityzer-backups"
}

# Versioning for recovery
resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle policy
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  
  rule {
    id = "archive-old-backups"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 365
    }
  }
}

# Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

## Disaster Recovery Plan

### DR Scenarios

#### Scenario 1: Single Node Failure
```
Detection: CloudWatch alarm + Node Not Ready
RTO: 5 minutes
Actions:
1. kubelet will reschedule pods to healthy nodes
2. Verify pod redistribution
3. Monitor resource utilization
4. No manual intervention usually needed
```

#### Scenario 2: Availability Zone Outage
```
Detection: Multiple node failures in same AZ
RTO: 10 minutes
Actions:
1. ASG launches replacement instances in other AZs
2. Load balancer shifts traffic automatically
3. RDS failover to standby (auto)
4. Verify service endpoints
```

#### Scenario 3: Region Failure
```
Detection: All services down in region
RTO: 30 minutes
Actions:
1. Activate secondary region cluster
2. Update DNS to point to secondary
3. Restore database from backup
4. Verify application functionality
5. Monitor for data loss
```

## Failover Procedures

### Automatic Failover (RDS)
```bash
#!/bin/bash
# RDS Automatic Failover Verification

DB_INSTANCE="audityzer-db-primary"
REGION="eu-west-1"

echo "Checking RDS Multi-AZ Status..."
aws rds describe-db-instances \
  --db-instance-identifier $DB_INSTANCE \
  --region $REGION \
  --query 'DBInstances[0].[DBInstanceStatus,MultiAZ,PendingModifiedValues]' \
  --output table

echo "Monitoring failover (if occurring)..."
while true; do
  STATUS=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE \
    --region $REGION \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text)
  
  echo "Current status: $STATUS at $(date)"
  
  if [ "$STATUS" = "available" ]; then
    break
  fi
  
  sleep 30
done

echo "RDS Failover completed"
```

### Manual Failover (Application)
```bash
#!/bin/bash
# Manual application failover to secondary region

PRIMARY_REGION="eu-west-1"
SECONDARY_REGION="eu-west-2"
CLUSTER_NAME="audityzer-eks"

echo "[1] Stopping primary cluster..."
aws eks update-cluster-config \
  --name $CLUSTER_NAME \
  --region $PRIMARY_REGION \
  --logging '{"clusterLogging":[{"enabled":false,"types":["api","audit","authenticator","controllerManager","scheduler"]}]}'

echo "[2] Starting secondary cluster..."
kubectl config use-context audityzer-secondary
kubectl scale deployment --all --replicas=2 -n production

echo "[3] Updating DNS records..."
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.audityzer.com",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "secondary-alb.eu-west-2.elb.amazonaws.com"}]
      }
    }]
  }'

echo "[4] Verifying connectivity..."
curl -I https://api.audityzer.com/health

echo "Failover completed"
```

## Testing and Validation

### Monthly DR Drill
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: dr-drill
  namespace: kube-system
spec:
  schedule: "0 2 1 * *"  # First day of month at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: dr-tester
            image: audityzer/dr-test:latest
            env:
            - name: TEST_BACKUP_RESTORE
              value: "true"
            - name: TEST_FAILOVER
              value: "false"
            - name: TEST_DNS_SWITCH
              value: "false"
          restartPolicy: OnFailure
```

### Backup Verification Script
```python
import boto3
import datetime
from botocore.exceptions import ClientError

def verify_backups():
    rds = boto3.client('rds', region_name='eu-west-1')
    s3 = boto3.client('s3', region_name='eu-west-1')
    
    # Check RDS automated backups
    response = rds.describe_db_instances(DBInstanceIdentifier='audityzer-db')
    db_instance = response['DBInstances'][0]
    
    backup_window = db_instance.get('BackupRetentionPeriod')
    if backup_window < 30:
        print(f"WARNING: Backup retention too short: {backup_window} days")
    
    # Check latest backup age
    backups = rds.describe_db_snapshots(
        DBInstanceIdentifier='audityzer-db',
        IncludeShared=False
    )
    
    if backups['DBSnapshots']:
        latest_backup = backups['DBSnapshots'][0]
        backup_age = datetime.datetime.now(datetime.timezone.utc) - latest_backup['SnapshotCreateTime']
        print(f"Latest RDS backup: {backup_age.days} days old")
    
    # Check S3 backups
    response = s3.list_objects_v2(Bucket='audityzer-backups')
    if 'Contents' in response:
        latest_s3 = max(response['Contents'], key=lambda x: x['LastModified'])
        s3_age = datetime.datetime.now(datetime.timezone.utc) - latest_s3['LastModified']
        print(f"Latest S3 backup: {s3_age.days} days old")

if __name__ == '__main__':
    verify_backups()
```

## Runbooks

### Runbook: Database Restore
```bash
#!/bin/bash
# Restore RDS from snapshot

set -e

SNAPSHOT_ID="audityzer-db-snapshot-20240115"
NEW_INSTANCE_ID="audityzer-db-restored-$(date +%s)"
REGION="eu-west-1"

echo "[1] Creating new instance from snapshot..."
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier $NEW_INSTANCE_ID \
  --db-snapshot-identifier $SNAPSHOT_ID \
  --region $REGION

echo "[2] Waiting for instance to become available..."
aws rds wait db-instance-available \
  --db-instance-identifier $NEW_INSTANCE_ID \
  --region $REGION

echo "[3] Modifying security groups..."
aws rds modify-db-instance \
  --db-instance-identifier $NEW_INSTANCE_ID \
  --vpc-security-group-ids sg-0123456789abcdef0 \
  --apply-immediately

echo "[4] Testing connectivity..."
ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier $NEW_INSTANCE_ID \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

psql -h $ENDPOINT -U admin -d audityzer -c "SELECT version();"

echo "[5] Swap DNS if healthy..."
echo "Review $NEW_INSTANCE_ID before swapping endpoints"
```

---
Last Updated: 2024-01-15
Version: 1.0.0
Author: Audityzer DevOps Team
