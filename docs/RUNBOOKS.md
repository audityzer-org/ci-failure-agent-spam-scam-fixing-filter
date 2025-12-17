docs/RUNBOOKS.md# Operational Runbooks
## Anti-Corruption Detection System

### Critical Incident Response

#### Service Down Alert (P1)
```bash
# 1. Immediate Assessment
kubectl get pods -n production -l app=anti-corruption
kubectl describe pod <pod-name> -n production
kubectl logs <pod-name> -n production --tail=50

# 2. Check Dependencies
kubectl get pods -n production | grep postgres
kubectl get pods -n production | grep redis

# 3. Force Pod Restart (if suspected)
kubectl delete pod <pod-name> -n production

# 4. Verify Recovery
kubectl wait --for=condition=Ready pod -l app=anti-corruption -n production --timeout=300s
curl https://api.audityzer.com/health/ready

# 5. Escalate if not resolved
echo "Alert escalation required" | notify-slack #oncall
```

#### High Error Rate (P1 > 5%)
```bash
# 1. Check Prometheus
kubectl port-forward -n monitoring prometheus-0 9090:9090
# Navigate to: http://localhost:9090
# Query: rate(http_requests_total{status=~"5.."}[5m])

# 2. Check Pod Logs
kubectl logs -f deployment/anti-corruption-orchestrator -n production --all-containers=true

# 3. Check Resource Constraints
kubectl top nodes
kubectl top pod -n production -l app=anti-corruption

# 4. Scale Up if Memory/CPU Limited
kubectl scale deployment anti-corruption-orchestrator --replicas=5 -n production

# 5. Rolling Restart
kubectl rollout restart deployment/anti-corruption-orchestrator -n production
kubectl rollout status deployment/anti-corruption-orchestrator -n production
```

#### Database Connection Pool Exhausted (P1)
```bash
# 1. Check Connection Count
psql -h $DB_HOST -c "SELECT count(*) FROM pg_stat_activity;"

# 2. Identify Long-Running Queries
psql -h $DB_HOST -c "SELECT pid, query FROM pg_stat_activity WHERE query NOT LIKE '%pg_stat_activity%' ORDER BY query_start DESC;"

# 3. Kill Idle Connections
psql -h $DB_HOST -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';"

# 4. Verify Connection Pool
kubectl logs -f deployment/anti-corruption-orchestrator -n production | grep -i connection

# 5. Restart Service
kubectl rollout restart deployment/anti-corruption-orchestrator -n production
```

### Deployment Issues

#### Failed Deployment
```bash
# 1. Check Deployment Status
kubectl describe deployment anti-corruption-orchestrator -n production
kubectl get events -n production --sort-by='.lastTimestamp' | tail -20

# 2. Check Image Availability
kubectl describe pod <pod-name> -n production | grep -A 10 "Image"

# 3. Rollback to Previous Version
kubectl rollout history deployment/anti-corruption-orchestrator -n production
kubectl rollout undo deployment/anti-corruption-orchestrator -n production
kubectl rollout status deployment/anti-corruption-orchestrator -n production

# 4. Via Helm
helm rollback anti-corruption -n production
helm status anti-corruption -n production
```

#### ImagePullBackOff Error
```bash
# 1. Verify Image Exists in Registry
aws ecr describe-images --repository-name anti-corruption --image-ids imageTag=latest

# 2. Check Image Pull Secrets
kubectl get secrets -n production
kubectl describe secret regcred -n production

# 3. Verify Credentials
kubectl delete secret regcred -n production
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<user> \
  --docker-password=<pass> \
  -n production

# 4. Retry Deployment
kubectl rollout restart deployment/anti-corruption-orchestrator -n production
```

### Network Issues

#### Service Unreachable
```bash
# 1. Verify Service
kubectl get svc -n production
kubectl describe svc anti-corruption -n production

# 2. Test Connectivity
kubectl run debug --image=busybox --rm -it -- sh
# Inside pod:
nslookup anti-corruption.production.svc.cluster.local
wget -O- http://anti-corruption:8080/health/ready

# 3. Check Network Policies
kubectl get networkpolicies -n production
kubectl describe networkpolicy default-deny-all -n production

# 4. Verify Ingress
kubectl describe ingress anti-corruption-ingress -n production
kubectl get ingress -n production
```

### Scaling Operations

#### Manual Scaling
```bash
# Increase Replicas
kubectl scale deployment anti-corruption-orchestrator --replicas=10 -n production
kubectl wait --for=condition=Ready pod -l app=anti-corruption -n production --timeout=600s

# Monitor Rollout
watch kubectl get pods -n production -l app=anti-corruption

# Verify Load Distribution
kubectl top pod -n production -l app=anti-corruption
```

#### HPA Status Check
```bash
# View Current State
kubectl get hpa -n production
kubectl describe hpa anti-corruption-hpa -n production

# Check Metrics
kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes | jq .
kubectl get --raw /apis/metrics.k8s.io/v1beta1/pods?namespace=production | jq .
```

### Monitoring & Debugging

#### Connect to Running Pod
```bash
# Execute Command
kubectl exec -it <pod-name> -n production -- /bin/sh

# Port Forward
kubectl port-forward <pod-name> 8080:8080 -n production

# Stream Logs
kubectl logs -f <pod-name> -n production
kubectl logs -f <pod-name> -n production --previous  # Previous crashed container
```

#### Collect Debug Information
```bash
# Pod Details
kubectl describe pod <pod-name> -n production > debug.txt

# Recent Events
kubectl get events -n production --sort-by='.lastTimestamp' | tail -100 >> debug.txt

# Resource Utilization
kubectl top nodes >> debug.txt
kubectl top pod -n production >> debug.txt

# Network Connectivity
kubectl get networkpolicies -n production >> debug.txt
```

### Maintenance Windows

#### Pre-Maintenance Checklist
- [ ] Check current request volume
- [ ] Verify all pods healthy
- [ ] Review recent error rates
- [ ] Notify on-call team
- [ ] Check dependent services
- [ ] Have rollback plan ready

#### During Maintenance
- [ ] Monitor metrics continuously
- [ ] Keep escalation contact available
- [ ] Document all changes
- [ ] Run smoke tests every 5 minutes

#### Post-Maintenance
- [ ] Verify all endpoints responding
- [ ] Check error rates baseline
- [ ] Review logs for issues
- [ ] Document any incidents
- [ ] Notify resolution to team

Add comprehensive operational runbooks for incident response
#### Backup Verification
```bash
# List Available Backups
aws s3 ls s3://audityzer-backups/databases/

# Restore from Backup
aws s3 cp s3://audityzer-backups/databases/latest.sql .
psql -h $DB_HOST -U $DB_USER < latest.sql
```

#### Full Cluster Recovery
```bash
# 1. Restore Infrastructure
terraform apply -auto-approve

# 2. Deploy Applications
kubectl apply -f gitops/argocd-application.yaml

# 3. Verify Services
kubectl get pods -A
kubectl get svc -A

# 4. Restore Data
aws s3 cp s3://audityzer-backups/data/ ./ --recursive
kubectl cp ./data deployment/anti-corruption-orchestrator:/data -n production
```

---
**Last Updated**: 2025-12-17
**On-Call Contact**: oncall@audityzer.com
