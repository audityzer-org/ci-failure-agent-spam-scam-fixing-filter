# Production Deployment Guide - Phase 1
## CI Failure Agent Spam Scam Fixing Filter

### Prerequisites

Before starting deployment to production, ensure you have:

1. **AWS Account Setup**
   - AWS CLI configured with appropriate credentials
   - Required IAM permissions for EKS, RDS, S3, CloudWatch
   - AWS region selected (recommended: us-east-1)

2. **Tools Installation**
   ```bash
   # Install required tools
   brew install awscli kubectl helm eksctl  # macOS
   # OR for Linux/Windows, use package managers or installers
   ```

3. **Container Registry**
   - Docker Hub account or AWS ECR repository
   - Push application image: `docker push <your-registry>/ci-failure-agent:latest`

### Step 1: Create EKS Cluster

```bash
# Create production EKS cluster
exksctl create cluster \
  --name ci-failure-agent-prod \
  --region us-east-1 \
  --nodegroup-name standard-nodes \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --version 1.28 \
  --zones us-east-1a,us-east-1b,us-east-1c

# Wait for cluster creation (~10-15 minutes)
eksctl get cluster --name ci-failure-agent-prod
```

### Step 2: Configure Kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --name ci-failure-agent-prod \
  --region us-east-1

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### Step 3: Create Production Namespace

```bash
# Create namespace
kubectl create namespace production

# Set default namespace
kubectl config set-context --current --namespace=production

# Verify
kubectl get namespace
```

### Step 4: Create Container Registry Secret

```bash
# Create docker credentials secret
kubectl create secret docker-registry regcred \
  --docker-server=<your-registry> \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email> \
  -n production
```

### Step 5: Deploy Application Manifests

```bash
# Deploy in correct order
kubectl apply -f k8s/deployment.yaml -n production
kubectl apply -f k8s/service.yaml -n production
kubectl apply -f k8s/ingress-storage-monitoring.yaml -n production

# Verify deployments
kubectl get deployments -n production
kubectl get pods -n production
kubectl get svc -n production
```

### Step 6: Configure Auto-Scaling

```bash
# Install metrics-server (required for HPA)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Create HorizontalPodAutoscaler
kubectl autoscale deployment ci-failure-agent \
  --cpu-percent=70 \
  --min=3 \
  --max=10 \
  -n production
```

### Health Checks

After deployment, verify:

```bash
# Check pod status
kubectl get pods -n production

# Check logs
kubectl logs -l app=ci-failure-agent -n production --all-containers=true

# Port forward to test locally
kubectl port-forward svc/ci-failure-agent 8000:80 -n production

# Health check
curl http://localhost:8000/health
```

### Monitoring & Logging Setup

See [Phase 3](../NEXT_STEPS.md) for detailed observability stack setup with Prometheus, Grafana, and Loki.

### Rollback Procedure

```bash
# Check deployment history
kubectl rollout history deployment/ci-failure-agent -n production

# Rollback to previous version
kubectl rollout undo deployment/ci-failure-agent -n production

# Rollback to specific revision
kubectl rollout undo deployment/ci-failure-agent --to-revision=2 -n production
```

### Troubleshooting

**Pods not starting**
```bash
kubectl describe pod <pod-name> -n production
kubectl logs <pod-name> -n production
```

**Image pull errors**
```bash
# Check secret
kubectl get secret regcred -n production

# Recreate if needed
kubectl delete secret regcred -n production
kubectl create secret docker-registry regcred ...
```

**Resource constraints**
```bash
kubectl top nodes
kubectl top pods -n production
```

### Production Checklist

- [ ] EKS cluster created and healthy
- [ ] kubectl configured and working
- [ ] All pods running and ready
- [ ] Services accessible
- [ ] Health checks passing
- [ ] Auto-scaling configured
- [ ] Monitoring enabled
- [ ] Backup strategy in place
