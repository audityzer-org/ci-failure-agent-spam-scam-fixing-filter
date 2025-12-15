# Operations and Maintenance Manual

## Overview
This manual provides operational guidelines, maintenance procedures, and troubleshooting steps for the Audityzer production infrastructure.

## Table of Contents
1. [Daily Operations](#daily-operations)
2. [Maintenance Windows](#maintenance-windows)
3. [Monitoring and Alerting](#monitoring-and-alerting)
4. [Troubleshooting](#troubleshooting)
5. [Common Tasks](#common-tasks)
6. [Escalation Procedures](#escalation-procedures)

## Daily Operations

### Health Checks
```bash
#!/bin/bash
# Daily health check script

echo "=== Cluster Health ==="
kubectl get nodes
kubectl top nodes
kubectl get pods --all-namespaces | grep -i error

echo "\n=== Database Health ==="
aws rds describe-db-instances --query 'DBInstances[?DBInstanceIdentifier==`audityzer-db`].{Status:DBInstanceStatus,CPU:PendingModifiedValues}'

echo "\n=== Storage Check ==="
kubectl get pv
kubectl get pvc --all-namespaces

echo "\n=== Network Health ==="
kubectl get svc --all-namespaces
aws elbv2 describe-load-balancers --query 'LoadBalancers[*].State'

echo "Health check completed at $(date)"
```

### Log Aggregation
```bash
#!/bin/bash
# Check application logs

NAMESPACE="production"

echo "Recent pod errors:"
kubectl logs -n $NAMESPACE -l app=api --tail=50 --all-containers=true | grep -i error

echo "\nRecent warnings:"
kubectl logs -n $NAMESPACE -l app=api --tail=100 --all-containers=true | grep -i warn

echo "\nPod restart count:"
kubectl get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{"\n"}{.metadata.name}{"\t"}{.status.containerStatuses[0].restartCount}{end}'
```

## Maintenance Windows

### Scheduled Maintenance
```
Monthly: First Sunday 2:00 AM - 4:00 AM UTC
- Database maintenance and optimization
- Certificate renewal checks
- Security patching
- Log rotation and cleanup

Weekly: Wednesday 3:00 AM UTC (30 min)
- Kubernetes version checking
- Dependency updates
- Cache warm-up
```

### Database Maintenance
```bash
#!/bin/bash
# Monthly database maintenance

echo "[1] Vacuum analyze on PostgreSQL..."
kubectl exec -i postgres-pod -c postgresql -- \
  psql -U admin -d audityzer -c "VACUUM ANALYZE;"

echo "[2] Update statistics..."
kubectl exec -i postgres-pod -c postgresql -- \
  psql -U admin -d audityzer -c "ANALYZE;"

echo "[3] Reindex if needed..."
kubectl exec -i postgres-pod -c postgresql -- \
  psql -U admin -d audityzer -c "REINDEX DATABASE audityzer;"

echo "[4] Check bloat..."
kubectl exec -i postgres-pod -c postgresql -- \
  psql -U admin -d audityzer -c "SELECT * FROM pg_stat_user_tables WHERE n_dead_tup > 1000;"
```

## Monitoring and Alerting

### Key Metrics to Monitor
```
Application Level:
- Request latency (p50, p95, p99)
- Error rate and error types
- Throughput (requests/sec)
- Cache hit ratio

Infrastructure Level:
- CPU utilization (>80% alert)
- Memory utilization (>85% alert)
- Disk usage (>90% alert)
- Network I/O and latency

Database Level:
- Connection pool utilization
- Query execution time
- Replication lag
- Transaction rate
```

### Creating Custom Alerts
```hcl
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "audityzer-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ErrorRate"
  namespace           = "Audityzer/API"
  period              = 300
  statistic           = "Average"
  threshold           = 5  # 5% error rate
  
  alarm_actions = [aws_sns_topic.alerts.arn]
  
  alarm_description = "Alert when error rate exceeds 5%"
}
```

## Troubleshooting

### Pod Debugging
```bash
#!/bin/bash
# Debug stuck or failing pod

POD_NAME="api-deployment-5d4f7b9c8-abc12"
NAMESPACE="production"

echo "[1] Describe pod..."
kubectl describe pod $POD_NAME -n $NAMESPACE

echo "\n[2] Check logs..."
kubectl logs $POD_NAME -n $NAMESPACE --previous  # Last run if crashed
kubectl logs $POD_NAME -n $NAMESPACE --all-containers=true

echo "\n[3] Get resource usage..."
kubectl top pod $POD_NAME -n $NAMESPACE

echo "\n[4] Check events..."
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'

echo "\n[5] Port forward for debugging..."
# kubectl port-forward $POD_NAME 8080:8080 -n $NAMESPACE
```

### Database Connection Issues
```bash
#!/bin/bash
# Test database connectivity

DB_HOST="audityzer-db.abc123.eu-west-1.rds.amazonaws.com"
DB_PORT=5432
DB_USER="admin"
DB_NAME="audityzer"

echo "[1] Test network connectivity..."
nc -zv $DB_HOST $DB_PORT

echo "\n[2] Test DNS resolution..."
nslookup $DB_HOST

echo "\n[3] Test database connection..."
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT NOW();"

echo "\n[4] Check connection pool..."
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \
  "SELECT usename, count(*) FROM pg_stat_activity GROUP BY usename;"

echo "\n[5] Check slow queries..."
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \
  "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

### CPU/Memory Issues
```bash
#!/bin/bash
# Diagnose high CPU/memory usage

echo "[1] Find resource-heavy pods..."
kubectl top pods --all-namespaces | sort -k3 -rn | head -10

echo "\n[2] Check node resources..."
kubectl describe nodes | grep -E 'Name:|Allocated resources|Limits'

echo "\n[3] Check HPA status..."
kubectl get hpa --all-namespaces
kubectl describe hpa <hpa-name> -n <namespace>

echo "\n[4] Review metrics from Prometheus..."
# kubectl port-forward svc/prometheus 9090:9090 -n monitoring
# Then visit: http://localhost:9090

echo "\n[5] Check pod resource requests/limits..."
kubectl get pods -n production -o jsonpath='{range .items[*]}{"\n"}{.metadata.name}{"\t"}{.spec.containers[0].resources}{end}'
```

## Common Tasks

### Rolling Update
```bash
#!/bin/bash
# Deploy new version with zero downtime

IMAGE="audityzer/api:v1.2.3"
DEPLOYMENT="api"
NAMESPACE="production"

echo "Starting rolling update..."
kubectl set image deployment/$DEPLOYMENT \
  api=$IMAGE \
  -n $NAMESPACE \
  --record

echo "Monitoring rollout..."
kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE --timeout=10m

echo "Verify health..."
kubectl get pods -n $NAMESPACE -l app=api
```

### Certificate Renewal
```bash
#!/bin/bash
# Check and renew certificates

echo "[1] Check certificate expiration..."
kubectl get secret audityzer-tls -o jsonpath='{.data.tls\.crt}' | \
  base64 --decode | openssl x509 -noout -enddate

echo "\n[2] Renew certificate if needed..."
certbot renew --dry-run  # Test
certbot renew  # Production

echo "\n[3] Update Kubernetes secret..."
kubectl create secret tls audityzer-tls \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem \
  --dry-run=client -o yaml | kubectl apply -f -

echo "\n[4] Restart ingress..."
kubectl rollout restart deployment/ingress-nginx -n ingress-nginx
```

### Scaling Operations
```bash
#!/bin/bash
# Manual scaling

echo "Current replicas:"
kubectl get deployment api -n production

echo "\nScaling to 5 replicas..."
kubectl scale deployment api --replicas=5 -n production

echo "\nWaiting for rollout..."
kubectl rollout status deployment/api -n production

echo "\nVerify pods..."
kubectl get pods -n production -l app=api
```

## Escalation Procedures

### On-Call Escalation
```
Level 1 - Application Team (15 minutes)
- Investigate logs and metrics
- Restart pods if needed
- Check deployment status

Level 2 - DevOps Team (30 minutes)
- Check infrastructure health
- Database analysis
- Network diagnostics
- Failover if necessary

Level 3 - Platform Team (1 hour)
- Architecture review
- Deep debugging
- Vendor escalation
- Executive notification
```

### Contact Information
```
Application Support: app-oncall@audityzer.com
Infrastructure Support: infra-oncall@audityzer.com
Database DBA: dba@audityzer.com
Security Team: security@audityzer.com
Executive: cto@audityzer.com (critical only)
```

---
Last Updated: 2024-01-15
Version: 1.0.0
Author: Audityzer Operations Team
