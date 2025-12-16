# CI Failure Agent Production Operations Runbook

**Version:** 1.0.0  
**Date:** December 16, 2025  
**Status:** Production Ready  
**Classification:** Internal Operations Guide

---

## 1. Executive Summary

This runbook provides comprehensive operational procedures for managing the CI Failure Agent in production. It covers daily operations, troubleshooting, scaling, and incident response.

**System Components:**
- AWS EC2 Instance (t3.micro, us-east-1)
- RDS PostgreSQL Database
- Redis Cache Layer
- Render.com UI Service
- GitHub Actions CI/CD Pipeline
- Monitoring: Prometheus, Grafana, Loki

---

## 2. Pre-Go-Live Checklist

### Infrastructure Status ✓
- [x] EC2 Instance running (t3.micro, 3/3 health checks passing)
- [x] RDS PostgreSQL database operational
- [x] Redis cache configured and tested
- [x] Security groups properly configured
- [x] HTTPS certificates provisioned
- [x] DNS records configured at Unstoppable Domains

### Application Status ✓
- [x] API health endpoints responding
- [x] UI service live on Render.com
- [x] All core features functional
- [x] Production deployment verified
- [x] Security audit passed
- [x] Cost structure optimized

### Documentation Status ✓
- [x] Production Readiness Report completed
- [x] GO-LIVE Announcement published
- [x] Operator Runbook created
- [x] Incident Response Playbook available
- [x] API documentation finalized
- [x] Deployment procedures documented

---

## 3. Daily Operations

### 3.1 Morning Health Check (UTC-5, 6:00 AM)

```bash
# 1. Check EC2 Instance Status
AWS Console → EC2 → Instances
- Verify instance state: Running
- Verify status checks: 3/3 Passed
- CPU Utilization: < 20%
- Network: Normal traffic

# 2. Check RDS Database
AWS Console → RDS → Databases
- Status: Available
- CPU: < 15%
- Storage: Monitor usage
- Connection count: Normal range (2-5)

# 3. Check API Health
curl https://api.auditorsec.com/health
# Expected: {"status": "healthy", "service": "CI Failure Agent", ...}

# 4. Check UI Service
Visit https://auditorsec.com
# Verify page loads in < 3 seconds

# 5. Monitor Logs
Render Dashboard → ci-failure-agent-ui → Logs
- Check for errors
- Monitor for warnings
- Verify request patterns
```

### 3.2 Performance Monitoring (Hourly)

**Metrics to Monitor:**
- API Response Time: Target < 500ms (p95)
- Database Query Time: Target < 200ms (p95)
- Error Rate: Target < 0.1%
- Cache Hit Rate: Target > 85%
- CPU Utilization: Target < 30%
- Memory Usage: Target < 60%

**Monitoring Dashboard:**
- Grafana: http://34.235.128.213:3001 (Internal access via EC2 SSH tunnel)
- Prometheus: http://34.235.128.213:9090
- Loki Logs: Integrated in Grafana

### 3.3 Backup Operations (Daily at 2:00 AM UTC-5)

**Automated RDS Backups:**
- Retention: 7 days (configurable in Terraform)
- Backup Window: 02:00-03:00 UTC-5
- Multi-AZ: Disabled (Free tier)
- Status: AWS automated snapshots

**Manual Backup Procedure:**
```bash
# If manual backup needed
AWS CLI:
aws rds create-db-snapshot --db-instance-identifier ci-failure-agent-db \
  --db-snapshot-identifier ci-failure-agent-db-backup-$(date +%Y%m%d-%H%M%S)
```

---

## 4. Scaling Procedures

### 4.1 Vertical Scaling (Upgrade EC2 Instance)

**When to Scale:**
- CPU sustained > 70% for > 10 minutes
- Memory usage > 80%
- I/O wait > 20%

**Procedure:**
1. Create AMI snapshot of current instance
2. Launch new t3.small instance (next tier)
3. Copy EBS volumes to new instance
4. Update security group associations
5. Update Route 53 DNS if needed
6. Terminate old instance after verification

### 4.2 Horizontal Scaling (Add EC2 Instances)

**Load Balancing Setup:**
- Use AWS Application Load Balancer (ALB)
- Create Auto Scaling Group
- Set min=1, desired=2, max=4
- Health check interval: 30 seconds

**Terraform Configuration:**
```hcl
# Modify terraform/main.tf
resource "aws_autoscaling_group" "ci_failure_agent" {
  desired_capacity = 2
  max_size         = 4
  min_size         = 1
}
```

---

## 5. Common Issues & Troubleshooting

### 5.1 API Response Timeout (500+ ms)

**Diagnosis:**
```bash
# 1. Check API logs
Render Dashboard → ci-failure-agent-ui → Logs

# 2. Check database performance
AWS RDS → Performance Insights

# 3. Check Redis cache
redis-cli -h <redis-host> INFO stats
```

**Solutions:**
- [ ] Increase database connection pool
- [ ] Clear Redis cache if corrupted
- [ ] Upgrade EC2 instance size
- [ ] Optimize slow queries (check Slow Query Log)
- [ ] Enable database query caching

### 5.2 Database Connection Pool Exhausted

**Error:**  `too many connections`

**Diagnosis:**
```sql
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;
```

**Solutions:**
- [ ] Increase `max_connections` in RDS parameter group
- [ ] Implement connection pooling (PgBouncer)
- [ ] Kill idle connections
- [ ] Review application for connection leaks

### 5.3 Out of Memory (OOM)

**Symptoms:**
- Service crashes or restarts
- High memory usage before crash
- No disk space errors

**Solutions:**
- [ ] Increase EC2 instance RAM
- [ ] Enable memory swap (AWS)
- [ ] Optimize application memory usage
- [ ] Reduce cache size if necessary
- [ ] Implement memory monitoring alerts

### 5.4 Disk Space Critical

**Monitoring:**
```bash
# SSH to EC2 instance
df -h
du -sh /var/lib/postgresql/*
```

**Solutions:**
- [ ] Extend EBS volume size
- [ ] Archive old logs
- [ ] Clean temporary files
- [ ] Vacuum PostgreSQL database

---

## 6. Maintenance Tasks

### 6.1 Weekly Database Maintenance (Sunday 3:00 AM UTC-5)

```sql
-- VACUUM ANALYZE (reclaim space and update statistics)
VACUUM ANALYZE;

-- Check and reindex if needed
REINDEX DATABASE ci_failure_agent_db;

-- Check for unused indexes
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

### 6.2 Monthly Security Patching (First Tuesday of Month)

**Steps:**
1. Schedule maintenance window (Off-peak hours)
2. Take RDS snapshot
3. Apply security patches to EC2
4. Update Docker images
5. Run security vulnerability scan
6. Update dependencies (if needed)

### 6.3 Quarterly Disaster Recovery Test (Every 90 days)

**Testing Procedure:**
1. Restore from latest RDS snapshot to test database
2. Verify data integrity
3. Test failover procedures
4. Document recovery time (RTO)
5. Document data loss (RPO)

---

## 7. Incident Response

### 7.1 Service Down (0 Available)

**Severity:** CRITICAL (SEV1)  
**Response Time:** < 5 minutes

**Immediate Actions:**
1. [ ] Verify service is actually down (check multiple endpoints)
2. [ ] Check AWS service health dashboard
3. [ ] Review EC2 instance status
4. [ ] Check RDS instance status
5. [ ] Review recent deployments

**Recovery Options:**
- Option A: Restart EC2 instance
- Option B: Rollback recent deployment
- Option C: Fail over to backup instance
- Option D: Restore from snapshot

### 7.2 High Error Rate (> 5%)

**Severity:** HIGH (SEV2)  
**Response Time:** < 15 minutes

**Diagnosis:**
- [ ] Check application logs for error patterns
- [ ] Monitor database query errors
- [ ] Review Redis cache errors
- [ ] Check for DDoS or malicious traffic

**Mitigation:**
- [ ] Rate limiting (activate WAF rules)
- [ ] Scale instances horizontally
- [ ] Restart problematic service
- [ ] Clear corrupted cache

### 7.3 Database Unavailable

**Severity:** CRITICAL (SEV1)  
**Response Time:** < 5 minutes

**Diagnosis:**
```bash
# Check RDS status
aws rds describe-db-instances --db-instance-identifier ci-failure-agent-db

# Check connectivity from EC2
ssh ec2-user@<instance-ip>
pg_isready -h <rds-endpoint> -U postgres
```

**Recovery:**
- [ ] Reboot RDS instance
- [ ] Check security group rules
- [ ] Verify network ACLs
- [ ] Restore from latest snapshot if corrupted

---

## 8. Escalation Policy

**On-Call Rotation:** Maintained in GitHub Team Settings

**Escalation Chain:**
1. **Level 1** (0-15 min): Primary on-call engineer
2. **Level 2** (15-30 min): Secondary on-call + Team Lead
3. **Level 3** (30+ min): Engineering Manager + Infrastructure Team

**Contact Information:**
- Primary: romanchaa997 (GitHub notifications)
- Slack: #ci-failure-agent-incidents
- PagerDuty: [Link to PagerDuty] (if configured)

---

## 9. Deployment Procedures

### 9.1 Rolling Deployment (Zero-Downtime)

```bash
# 1. Create new AMI from current instance
aws ec2 create-image --instance-id <instance-id> --name ci-failure-agent-<version>

# 2. Launch new instance from AMI
aws ec2 run-instances --image-id <new-ami-id> --instance-type t3.micro

# 3. Update Route 53 DNS
aws route53 change-resource-record-sets --hosted-zone-id <zone-id> \
  --change-batch file://dns-update.json

# 4. Wait for health checks to pass
# Monitor: AWS EC2 Status Checks

# 5. Terminate old instance
aws ec2 terminate-instances --instance-ids <old-instance-id>
```

### 9.2 Deployment Rollback

```bash
# If deployment causes issues:

# 1. Identify last known good version
git log --oneline -n 20

# 2. Revert to previous commit
git revert <commit-hash>

# 3. Push to main branch
git push origin main

# 4. Monitor GitHub Actions workflow
# Actions automatically deploy via CI/CD
```

---

## 10. Contact & Escalation

**Technical Lead:** romanchaa997  
**Repository:** https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter  
**Documentation:** See PRODUCTION_READINESS_REPORT_DECEMBER_16.md  
**Incident Channel:** #ci-failure-agent-incidents  

---

**Last Updated:** December 16, 2025  
**Next Review:** March 16, 2026 (Quarterly)
