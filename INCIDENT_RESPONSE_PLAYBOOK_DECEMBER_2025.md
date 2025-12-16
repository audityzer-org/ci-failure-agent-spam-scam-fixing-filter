# CI Failure Agent - Incident Response Playbook

**Version:** 1.0.0 | **Date:** December 16, 2025 | **Severity Levels:** SEV0-SEV4

---

## 1. Severity Classification Matrix

| Severity | Impact | Response Time | Example |
|----------|--------|----------------|----------|
| **SEV0** | All services down | < 5 min | Complete system outage |
| **SEV1** | Critical functionality unavailable | < 15 min | API not responding |
| **SEV2** | Major functionality degraded | < 30 min | 50%+ error rate |
| **SEV3** | Minor feature broken | < 2 hours | UI rendering issue |
| **SEV4** | Cosmetic/documentation issue | < 1 day | Typo in logs |

---

## 2. Incident Command Structure

### Role Assignments
- **Incident Commander:** Directs response, communicates status
- **Technical Lead:** Coordinates technical remediation
- **Communication Lead:** Updates stakeholders
- **Scribe:** Documents timeline and decisions

### Escalation Path
```
Level 1 (0-15 min): On-call engineer + Slack alert
  ↓ (if unresolved)
Level 2 (15-30 min): Team lead + Engineering manager
  ↓ (if unresolved)  
Level 3 (30+ min): VP Engineering + Infrastructure team
```

---

## 3. SEV0: Complete System Outage

### Detection
- Primary health check: `GET https://api.auditorsec.com/health` → No response
- Secondary check: `GET http://34.235.128.213:8000/health` → Timeout
- UI status: auditorsec.com → 503 or timeout

### Immediate Actions (0-5 min)
```
1. [ ] Declare SEV0 incident in #incidents channel
2. [ ] Start war room (Zoom: [link to war room])
3. [ ] Verify outage scope (check multiple endpoints)
4. [ ] Check AWS service health dashboard
5. [ ] Check recent deployments/changes
6. [ ] Initiate incident timeline (Scribe task)
```

### Diagnostics (5-10 min)
```bash
# Check EC2 instance
aws ec2 describe-instance-status --instance-ids i-0e2f227c2f3a071a2

# Check RDS database
aws rds describe-db-instances --db-instance-identifier ci-failure-agent-db

# Try SSH to instance
ssh -i ~/.ssh/ci-failure-agent-key ec2-user@34.235.128.213

# If SSH works, check application logs
journalctl -u ci-failure-agent -n 100
```

### Recovery Options (Priority Order)
```
Option A (2 min): Restart EC2 instance
  aws ec2 reboot-instances --instance-ids i-0e2f227c2f3a071a2
  
Option B (5 min): Restart application service
  ssh ec2-user@34.235.128.213
  sudo systemctl restart ci-failure-agent
  
Option C (10 min): Rollback recent deployment
  git revert <bad-commit-hash>
  git push origin main
  (Wait for GitHub Actions to deploy)
  
Option D (20 min): Restore from snapshot
  aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier ci-failure-agent-db-restored \
    --db-snapshot-identifier <latest-snapshot>
```

### Post-Recovery (Verification)
```
[ ] Health check returns 200 OK
[ ] API responds within 500ms
[ ] UI loads without errors
[ ] Database connections normal
[ ] No error spikes in logs
[ ] Notify all stakeholders
```

### Post-Incident
- [ ] Create post-mortem document
- [ ] Schedule blameless review within 48 hours
- [ ] Document root cause
- [ ] Implement preventive measures
- [ ] Update runbooks if needed

---

## 4. SEV1: Critical Functionality Degraded

### Examples
- API responding with 50%+ 500 errors
- Database query timeouts > 5 seconds
- Cache failures affecting all requests
- HTTPS certificate expired/invalid

### Response Timeline
```
0-5 min:  Declare incident, gather data
5-15 min: Identify root cause, apply fix
15+ min:  Implement permanent solution
```

### Diagnosis Commands
```bash
# Check error logs
aws logs tail /aws/ci-failure-agent/api --follow

# Check database performance
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=ci-failure-agent-db \
  --start-time 2025-12-16T20:00:00Z \
  --end-time 2025-12-16T21:00:00Z \
  --period 60 \
  --statistics Average,Maximum

# Check API response times
curl -w "Response time: %{time_total}s\n" https://api.auditorsec.com/health
```

### Common Solutions
- Increase database connection pool
- Clear Redis cache
- Scale up EC2 instance
- Restart database connection pool
- Kill long-running queries

---

## 5. SEV2: Major Feature Degradation

### Characteristics
- Service partially available (>30% errors)
- Performance significantly impacted
- User experience noticeably affected

### Response Actions
```
1. Alert team but no war room required
2. Investigate over 30 minutes
3. Can be resolved during business hours
4. Document for post-analysis
```

---

## 6. Communication Template

### Initial Notification (Immediately)
```
🚨 INCIDENT ALERT - SEV0

Service: CI Failure Agent API
Status: OUTAGE - No response
Detected: 2025-12-16T20:53:45Z
Expected Resolution: TBD

Updates will be posted every 5 minutes
War Room: [Zoom Link]
```

### Status Update (Every 5 minutes during incident)
```
🔄 UPDATE - 30 minutes into incident

Root Cause: Database connection pool exhausted
Current Action: Scaling RDS connections
Estimated Resolution: 10 minutes
Next Update: 21:03 UTC
```

### Resolution Notification
```
✅ RESOLVED

Service: CI Failure Agent API
Resolution Time: 45 minutes
Root Cause: Runaway query consuming connections
Fix Applied: Killed offending connection, optimized query

Post-mortem review scheduled for 2025-12-17 10:00 UTC
```

---

## 7. Runbook References

- Daily Operations: See OPERATOR_RUNBOOK_PRODUCTION_DECEMBER_2025.md
- Monitoring: See PHASE_4_5_API_AND_MONITORING.md
- Scaling: See DEPLOYMENT_EXECUTION_PLAYBOOK.md

---

**Last Updated:** December 16, 2025  
**Next Review:** March 16, 2026
