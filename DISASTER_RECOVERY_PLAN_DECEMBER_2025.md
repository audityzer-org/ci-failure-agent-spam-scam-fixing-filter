# Disaster Recovery & Business Continuity Plan

## Recovery Objectives
- **RTO (Recovery Time Objective):** < 1 hour
- **RPO (Recovery Point Objective):** < 15 minutes
- **Availability Target:** 99.9% SLA

## Backup Strategy
- **RDS:** Automated daily snapshots (7-day retention)
- **Application:** Docker images in ECR
- **Data:** S3 cross-region replication
- **Frequency:** Real-time incremental backups

## Failover Procedures

### Database Failover (15 min)
1. Promote read replica to primary
2. Update connection strings
3. Run data integrity checks
4. Notify stakeholders

### Application Failover (5 min)
1. Launch new EC2 from latest AMI
2. Attach EBS volumes
3. Update Route53 DNS
4. Health check validation

### Regional Failover (30 min)
1. Activate DR region (us-west-2)
2. Restore RDS from snapshot
3. Deploy application containers
4. Run smoke tests
5. Switch DNS to DR region

## Testing
- Monthly failover drills
- Quarterly full DR test
- Annual multi-region test
- Document all findings

---
**Last Updated:** December 16, 2025
