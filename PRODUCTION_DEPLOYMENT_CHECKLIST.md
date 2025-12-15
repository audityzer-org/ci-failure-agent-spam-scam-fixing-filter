# Production Deployment Checklist

## Pre-Deployment Phase

### Code Review & Quality
- [ ] All pull requests reviewed and approved
- [ ] Test coverage >80%
- [ ] No security warnings from SonarQube
- [ ] OWASP dependency check passed
- [ ] Code complexity within acceptable limits

### Testing
- [ ] Unit tests passing (100%)
- [ ] Integration tests passing
- [ ] End-to-end tests in staging environment
- [ ] Performance testing completed
- [ ] Load testing shows acceptable latency
- [ ] Security scanning completed

### Documentation
- [ ] API documentation updated
- [ ] Change log updated
- [ ] Migration scripts tested
- [ ] Rollback procedure documented
- [ ] Known issues documented

## Infrastructure Preparation

### Database
- [ ] Database migrations tested on staging
- [ ] Backup created and verified
- [ ] Monitoring alerts configured
- [ ] Connection pool settings optimized
- [ ] Indexes reviewed for new queries

### Kubernetes
- [ ] Image built and scanned for vulnerabilities
- [ ] Image pushed to ECR
- [ ] Deployment manifests reviewed
- [ ] Resource limits set appropriately
- [ ] Health checks configured
- [ ] Network policies applied

### Secrets & Configuration
- [ ] All environment variables configured
- [ ] API keys rotated if needed
- [ ] Database credentials secure
- [ ] TLS certificates valid
- [ ] SSH keys configured

## Deployment Phase

### Pre-Deployment Checks
- [ ] Cluster health verified (all nodes healthy)
- [ ] Storage space available
- [ ] Network connectivity verified
- [ ] Monitoring and logging enabled
- [ ] Backup completed

### Deployment Execution
- [ ] Maintenance window scheduled
- [ ] Incident commander assigned
- [ ] Communication channels open
- [ ] Rollback plan verified
- [ ] All stakeholders notified

### Deployment Steps
```
1. [ ] Deploy to canary (5% traffic)
2. [ ] Monitor canary for 10 minutes
3. [ ] Check error rates and latency
4. [ ] Expand to 50% (blue-green)
5. [ ] Monitor for 15 minutes
6. [ ] If healthy, expand to 100%
7. [ ] Monitor for 30 minutes
8. [ ] Update DNS/load balancer
```

## Post-Deployment Phase

### Verification
- [ ] All endpoints responding
- [ ] Error rate <0.1%
- [ ] Latency p99 <500ms
- [ ] Database queries performing
- [ ] Cache hit rates normal
- [ ] No unexpected resource usage

### Monitoring
- [ ] CloudWatch metrics reviewed
- [ ] Application logs clean
- [ ] No critical alerts
- [ ] User reports reviewed

### Communication
- [ ] Deployment status posted
- [ ] Stakeholders notified
- [ ] Incident ticket resolved
- [ ] Post-deployment report started

## Rollback Scenario

If deployment fails:
1. [ ] Trigger automatic rollback
2. [ ] Verify previous version running
3. [ ] Check data consistency
4. [ ] Notify stakeholders
5. [ ] Schedule incident review
6. [ ] Create bug report

---
Version: 1.0.0
Last Updated: 2024-01-15
