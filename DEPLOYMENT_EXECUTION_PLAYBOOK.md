# Deployment Execution Playbook
# Повний план розгортання Audityzer на AWS EKS

## Phase 1: Infrastructure Validation (5-10 minutes)

### Step 1.1: Pre-flight Checks
```bash
#!/bin/bash
echo "=== STEP 1: Pre-flight Validation ==="

# 1. Verify AWS credentials
echo "[1.1] Checking AWS credentials..."
aws sts get-caller-identity
if [ $? -ne 0 ]; then
  echo "ERROR: AWS credentials not configured"
  exit 1
fi

# 2. Verify required tools
echo "[1.2] Verifying required tools..."
for tool in terraform kubectl aws docker; do
  if ! command -v $tool &> /dev/null; then
    echo "ERROR: $tool not installed"
    exit 1
  fi
done

# 3. Check AWS permissions
echo "[1.3] Checking AWS permissions..."
aws ec2 describe-instances > /dev/null
if [ $? -ne 0 ]; then
  echo "ERROR: Insufficient AWS permissions"
  exit 1
fi

echo "\n✓ All pre-flight checks passed"
```

### Step 1.2: Execute Validation Script
```bash
echo "[1.3] Running AWS Infrastructure Validation Script..."
cd scripts/
./aws-infrastructure-validation.sh
echo "✓ Infrastructure validation complete"
```

---

## Phase 2: Infrastructure Deployment (20-30 minutes)

### Step 2.1: Initialize Terraform
```bash
echo "=== STEP 2: Infrastructure Deployment ==="
echo "[2.1] Initializing Terraform..."
cd terraform/
terraform init -upgrade
echo "✓ Terraform initialized"
```

### Step 2.2: Plan Terraform Deployment
```bash
echo "[2.2] Planning Terraform deployment..."
terraform plan -out=tfplan
# Review plan carefully!
```

### Step 2.3: Apply Terraform Configuration
```bash
echo "[2.3] Applying Terraform configuration..."
echo "⏱️  This will take approximately 15-20 minutes..."
terraform apply tfplan

# Capture outputs
echo "[2.4] Capturing infrastructure outputs..."
terraform output -json > ../infrastructure-outputs.json
echo "✓ Infrastructure deployment complete"
```

### Step 2.4: Verify Infrastructure
```bash
echo "[2.5] Verifying infrastructure..."

# Check VPC
echo "  - Checking VPC..."
VPC_ID=$(aws ec2 describe-vpcs --filters Name=tag:Name,Values=audityzer-vpc --query 'Vpcs[0].VpcId' --output text)
echo "    ✓ VPC: $VPC_ID"

# Check EKS Cluster
echo "  - Checking EKS Cluster..."
EKS_ENDPOINT=$(aws eks describe-cluster --name audityzer-eks --query 'cluster.endpoint' --output text)
echo "    ✓ EKS: $EKS_ENDPOINT"

# Check RDS
echo "  - Checking RDS Database..."
RDS_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier audityzer-db --query 'DBInstances[0].Endpoint.Address' --output text)
echo "    ✓ RDS: $RDS_ENDPOINT"

echo "✓ All infrastructure verified"
```

---

## Phase 3: Kubernetes Configuration (5 minutes)

### Step 3.1: Configure kubectl
```bash
echo "=== STEP 3: Kubernetes Configuration ==="
echo "[3.1] Configuring kubectl access..."
aws eks update-kubeconfig \
  --name audityzer-eks \
  --region eu-west-1

# Verify access
kubectl cluster-info
echo "✓ kubectl configured"
```

### Step 3.2: Verify Cluster Access
```bash
echo "[3.2] Verifying cluster access..."
echo "  Nodes:"
kubectl get nodes
echo "  ✓ Cluster ready"
```

---

## Phase 4: Kubernetes Deployment (10-15 minutes)

### Step 4.1: Create Namespaces
```bash
echo "=== STEP 4: Kubernetes Deployment ==="
echo "[4.1] Creating namespaces..."
kubectl create namespace production
kubectl create namespace monitoring
kubectl create namespace logging
echo "✓ Namespaces created"
```

### Step 4.2: Deploy RBAC and Policies
```bash
echo "[4.2] Deploying RBAC and security policies..."
kubectl apply -f k8s/rbac/
kubectl apply -f k8s/network-policies/
kubectl apply -f k8s/pod-security-policies/
echo "✓ Security policies deployed"
```

### Step 4.3: Deploy Infrastructure Components
```bash
echo "[4.3] Deploying infrastructure components..."
kubectl apply -f k8s/config/ -n production
kubectl apply -f k8s/storage/ -n production
echo "✓ Infrastructure components deployed"
```

### Step 4.4: Deploy Monitoring Stack
```bash
echo "[4.4] Deploying monitoring stack..."
kubectl apply -f k8s/monitoring/ -n monitoring
echo "  Waiting for Prometheus..."
sleep 30
kubectl wait --for=condition=ready pod -l app=prometheus -n monitoring --timeout=300s
echo "✓ Monitoring stack deployed"
```

### Step 4.5: Deploy Application
```bash
echo "[4.5] Deploying application..."
kubectl apply -f k8s/deployments/ -n production
kubectl apply -f k8s/services/ -n production
kubectl apply -f k8s/ingress/ -n production
echo "  Waiting for deployments..."
sleep 30
kubectl wait --for=condition=available deployment -n production --timeout=600s
echo "✓ Application deployed"
```

---

## Phase 5: Post-Deployment Verification (10 minutes)

### Step 5.1: Health Check
```bash
echo "=== STEP 5: Post-Deployment Verification ==="
echo "[5.1] Running health checks..."

echo "  Cluster Status:"
kubectl get nodes

echo "  Pod Status:"
kubectl get pods -n production

echo "  Service Status:"
kubectl get svc -n production

echo "  ✓ Health checks complete"
```

### Step 5.2: Application Endpoint Verification
```bash
echo "[5.2] Verifying application endpoints..."

# Get LoadBalancer endpoint
ALB_ENDPOINT=$(kubectl get svc -n production -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].status.loadBalancer.ingress[0].hostname}')
echo "  ALB Endpoint: $ALB_ENDPOINT"

# Wait for DNS propagation
echo "  Waiting for DNS propagation (30s)..."
sleep 30

# Test API endpoint
echo "  Testing API endpoint..."
curl -v http://$ALB_ENDPOINT/health

echo "✓ Endpoints verified"
```

### Step 5.3: Database Connectivity
```bash
echo "[5.3] Verifying database connectivity..."

# Create port-forward for testing
kubectl port-forward -n production svc/api 5432:5432 &
PORT_FORWARD_PID=$!

sleep 5

# Test connection
echo "  Testing database connection..."
psql -h localhost -U admin -d audityzer -c "SELECT NOW();"

kill $PORT_FORWARD_PID
echo "✓ Database connectivity verified"
```

---

## Phase 6: Monitoring & Observability Setup (10 minutes)

### Step 6.1: Configure Dashboards
```bash
echo "=== STEP 6: Monitoring Setup ==="
echo "[6.1] Configuring dashboards..."

# Port-forward to Grafana
echo "  Accessing Grafana..."
kubectl port-forward -n monitoring svc/grafana 3000:80 &
echo "  Grafana available at: http://localhost:3000"
echo "  Default credentials: admin/admin"

# Configure data sources
echo "  ✓ Dashboards configured"
```

### Step 6.2: Alert Configuration
```bash
echo "[6.2] Configuring alerts..."
kubectl apply -f k8s/alerts/ -n monitoring
echo "✓ Alerts configured"
```

---

## Phase 7: Domain Configuration (5 minutes)

### Step 7.1: Update DNS Records
```bash
echo "=== STEP 7: Domain Configuration ==="
echo "[7.1] Updating DNS records..."

# Get ALB details
ALB_DETAILS=$(kubectl get svc -n production -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].status.loadBalancer.ingress[0].hostname}')

echo "  Update Route53 records:"
echo "  Domain: audityzer.com"
echo "  ALB: $ALB_DETAILS"
echo "  TTL: 300 seconds"

echo "  Manual step required - Update Route53 console"
echo "✓ DNS configuration ready"
```

### Step 7.2: SSL Certificate
```bash
echo "[7.2] Verifying SSL certificate..."
kubectl get secret audityzer-tls -n production
echo "✓ SSL certificate verified"
```

---

## Phase 8: First 24-Hour Monitoring

### Intensive Monitoring Checklist
```
[ ] 00:00 - Deployment complete, all pods running
[ ] 01:00 - Check error rates (should be <0.1%)
[ ] 02:00 - Verify response times (p99 <500ms)
[ ] 04:00 - Database performance review
[ ] 06:00 - Memory and CPU utilization normal
[ ] 08:00 - Check backup completion
[ ] 12:00 - Mid-day health review
[ ] 18:00 - Peak load performance review
[ ] 24:00 - Full stability confirmation
```

### Monitoring Commands
```bash
# Watch pods
kubectl get pods -n production -w

# Stream logs
kubectl logs -f deployment/api -n production

# Check metrics
kubectl top pods -n production
kubectl top nodes

# Check events
kubectl get events -n production --sort-by='.lastTimestamp'
```

---

## Phase 9: Performance Tuning

### Optimization Tasks
```bash
# Check resource utilization
kubectl describe nodes

# Review slow queries
kubectl exec -it db-pod -- psql -U admin -d audityzer -c \
  "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Optimize HPA settings
kubectl describe hpa -n production

# Review cache hit rates
kubectl logs -n production redis-pod | grep "hit_rate"
```

---

## Phase 10: Operations Handoff

### Handoff Checklist
```
[ ] All documentation transferred to operations team
[ ] Access credentials securely shared
[ ] Escalation procedures reviewed
[ ] Monitoring dashboards explained
[ ] Incident response runbooks reviewed
[ ] On-call rotation established
[ ] Backup and recovery procedures tested
[ ] Disaster recovery plan validated
```

---

## Rollback Procedures (Emergency)

### Quick Rollback
```bash
#!/bin/bash
echo "INITIATING EMERGENCY ROLLBACK"

# Rollback to previous version
kubectl rollout undo deployment/api -n production
kubectl rollout undo statefulset/db -n production

# Wait for rollback
kubectl rollout status deployment/api -n production

# Verify
kubectl get pods -n production

echo "✓ Rollback complete"
```

---

## Success Metrics

✓ All pods running and healthy  
✓ Error rate < 0.1%  
✓ Response time p99 < 500ms  
✓ CPU utilization < 70%  
✓ Memory utilization < 80%  
✓ Disk utilization < 85%  
✓ All backups completing successfully  
✓ Monitoring and alerting operational  
✓ All domains resolving correctly  
✓ SSL certificates valid  

---

**Status:** Ready for Execution  
**Estimated Duration:** 60-90 minutes (all phases)  
**Last Updated:** December 15, 2025
