# Production Deployment Guide
## CI/CD Failure Agent - Anti-Corruption Detection Platform

### Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Kubernetes Cluster Setup](#kubernetes-cluster-setup)
3. [Environment Configuration](#environment-configuration)
4. [Deployment Instructions](#deployment-instructions)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Pre-Deployment Checklist

### Prerequisites
- [ ] Kubernetes cluster (1.21+ recommended)
- [ ] kubectl CLI configured
- [ ] Docker registry access (for container images)
- [ ] PostgreSQL database (Neon or managed service)
- [ ] Google Cloud API credentials
- [ ] Domain name for ingress
- [ ] SSL/TLS certificate (Let's Encrypt or other CA)

### Required Tools
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm (optional but recommended)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install ingress-nginx
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install nginx-ingress ingress-nginx/ingress-nginx
```

---

## Kubernetes Cluster Setup

### Option 1: AWS EKS
```bash
# Create EKS cluster
eksctl create cluster \
  --name ci-failure-agent \
  --version 1.27 \
  --region us-east-1 \
  --nodegroup-name standard-nodes \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 6

# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name ci-failure-agent
```

### Option 2: Google GKE
```bash
# Create GKE cluster
gcloud container clusters create ci-failure-agent \
  --region us-central1 \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 6

# Get credentials
gcloud container clusters get-credentials ci-failure-agent --region us-central1
```

### Option 3: Azure AKS
```bash
# Create AKS cluster
az aks create \
  --resource-group ci-failure-agent-rg \
  --name ci-failure-agent-cluster \
  --node-count 3 \
  --vm-set-type VirtualMachineScaleSets \
  --load-balancer-sku standard

# Get credentials
az aks get-credentials --resource-group ci-failure-agent-rg --name ci-failure-agent-cluster
```

---

## Environment Configuration

### 1. Create Namespaces
```bash
kubectl create namespace production
kubectl create namespace monitoring
kubectl create namespace ingress-nginx
```

### 2. Create Secrets
```bash
# Database credentials
kubectl create secret generic app-secrets \
  --from-literal=database-url='postgresql://user:password@host:5432/dbname' \
  --from-literal=google-api-key='YOUR_GOOGLE_API_KEY' \
  -n production

# TLS Certificate
kubectl create secret tls ci-failure-agent-tls \
  --cert=path/to/cert.crt \
  --key=path/to/key.key \
  -n production
```

### 3. Create ConfigMaps
```bash
kubectl create configmap app-config \
  --from-literal=LOG_LEVEL=INFO \
  --from-literal=WORKERS=4 \
  -n production
```

---

## Deployment Instructions

### Deploy Kubernetes Manifests
```bash
# Navigate to k8s directory
cd k8s/

# Apply deployment
kubectl apply -f deployment.yaml -n production

# Apply services
kubectl apply -f service.yaml -n production

# Apply ingress, storage, and monitoring
kubectl apply -f ingress-storage-monitoring.yaml

# Verify deployment
kubectl get all -n production
```

### Verify Pod Status
```bash
# Check pod status
kubectl get pods -n production
kubectl describe pod -l app=ci-failure-agent -n production

# Check logs
kubectl logs -f deployment/ci-failure-agent -n production
```

---

## Post-Deployment Verification

### Health Checks
```bash
# Port forward to test health endpoint
kubectl port-forward svc/ci-failure-agent 8000:80 -n production &
curl http://localhost:8000/health

# Check service endpoints
kubectl get endpoints ci-failure-agent -n production

# Test ingress
curl https://api.ci-failure-agent.com/health
```

### Verify Monitoring
```bash
# Port forward to Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n monitoring &
open http://localhost:9090

# Check targets
kubectl logs -f deployment/prometheus -n monitoring
```

---

## Monitoring & Maintenance

### Scaling
```bash
# Manual scale
kubectl scale deployment/ci-failure-agent --replicas=5 -n production

# Horizontal Pod Autoscaler (recommended)
kubectl autoscale deployment ci-failure-agent \
  --min=2 --max=10 \
  --cpu-percent=80 -n production
```

### Updates
```bash
# Rolling update
kubectl set image deployment/ci-failure-agent \
  ci-failure-agent=audityzer-org/ci-failure-agent:v1.1.0 \
  -n production

# Rollback if needed
kubectl rollout undo deployment/ci-failure-agent -n production
```

### Backup & Recovery
```bash
# Backup persistent data
kubectl get pvc -n production
kubectl exec -it <pod-name> -- pg_dump -U user dbname > backup.sql

# Restore from backup
kubectl exec -it <pod-name> -- psql -U user dbname < backup.sql
```

---

## Troubleshooting

### Common Issues

**Issue: Pods not starting**
```bash
kubectl describe pod <pod-name> -n production
kubectl logs <pod-name> -n production
```

**Issue: Ingress not working**
```bash
kubectl get ingress -n production
kubectl describe ingress ci-failure-agent-ingress -n production
```

**Issue: Storage not mounting**
```bash
kubectl get pvc -n production
kubectl describe pvc postgres-pvc -n production
```

---

## Production Checklist

- [ ] All pods running (kubectl get pods -n production)
- [ ] Services accessible (kubectl get svc -n production)
- [ ] Ingress configured (kubectl get ingress)
- [ ] Monitoring operational (Prometheus dashboard)
- [ ] Database connected and tested
- [ ] API endpoints responding
- [ ] Health checks passing
- [ ] Logging configured
- [ ] Backups scheduled
- [ ] Alert rules configured
