# Production Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the CI Failure Agent to production environments on Render and Kubernetes.

## Prerequisites

- GitHub account with repository access
- Render account (render.com)
- Kubernetes cluster (EKS, GKE, or AKS)
- kubectl CLI installed and configured
- Docker installed for local testing
- Python 3.9+

## Part 1: Render Deployment (PaaS)

### 1.1 Create Render Account

1. Visit https://render.com
2. Sign up with GitHub account
3. Authorize repository access
4. Link billing information

### 1.2 Deploy Web Service

```bash
# Navigate to dashboard
# Click "New +" → "Web Service"
# Select repository: audityzer-org/ci-failure-agent-spam-scam-fixing-filter
# Select branch: main

# Configure service:
# Name: ci-failure-agent
# Environment: Python 3
# Build Command: pip install -r requirements.txt
# Start Command: gunicorn app:app --bind 0.0.0.0:$PORT
# Instance Type: Standard
```

### 1.3 Set Environment Variables

```bash
# In Render dashboard → Environment
# Add variables:
GOOGLE_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@host/db
REDIS_URL=redis://host:port
LOG_LEVEL=INFO
PORT=8000
WORKERS=4
TIMEOUT=120
```

### 1.4 Deploy Database (PostgreSQL)

```bash
# Click "New +" → "PostgreSQL"
# Name: ci-failure-agent-db
# PostgreSQL Version: 14
# Instance Type: Standard
# Initial Database: ciagent_prod
```

### 1.5 Configure Networking

```bash
# Get internal URL: ci-failure-agent-db.render.internal:5432
# Update DATABASE_URL in web service
# Format: postgresql://postgres:PASSWORD@ci-failure-agent-db.render.internal:5432/ciagent_prod
```

### 1.6 Deploy Redis (Optional)

```bash
# Click "New +" → "Redis"
# Name: ci-failure-agent-cache
# Memory: 256MB
# Get URL and add to REDIS_URL environment variable
```

### 1.7 Verify Deployment

```bash
# Check service logs
curl https://ci-failure-agent.onrender.com/health

# Expected response:
# {"status": "healthy", "timestamp": "2025-01-01T00:00:00Z"}
```

## Part 2: Kubernetes Deployment

### 2.1 Prepare Cluster

```bash
# Create namespace
kubectl create namespace ciagent
kubectl config set-context --current --namespace=ciagent

# Create secrets
kubectl create secret generic database-credentials \
  --from-literal=username=postgres \
  --from-literal=password=SecurePassword123

kubectl create secret generic api-keys \
  --from-literal=google-api-key=sk-...

# Create ConfigMap
kubectl create configmap app-config \
  --from-literal=LOG_LEVEL=INFO \
  --from-literal=WORKERS=4
```

### 2.2 Deploy Application

```bash
# Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Verify deployment
kubectl get deployments -n ciagent
kubectl get pods -n ciagent
kubectl get svc -n ciagent
```

### 2.3 Deploy Database

```bash
# Deploy PostgreSQL StatefulSet
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/postgres-pvc.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod \
  -l app=postgres --timeout=300s

# Run migrations
kubectl exec -it postgres-0 -- \
  psql -U postgres -d ciagent < /db/schema.sql
```

### 2.4 Configure Ingress

```bash
# Install nginx-ingress controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx

# Apply ingress configuration
kubectl apply -f k8s/ingress.yaml

# Get external IP
kubectl get ingress -n ciagent
# Update DNS to point to external IP
```

### 2.5 Setup Persistent Storage

```bash
# Create StorageClass
kubectl apply -f k8s/storage-class.yaml

# Create PersistentVolumeClaim
kubectl apply -f k8s/pvc-data.yaml
kubectl apply -f k8s/pvc-logs.yaml

# Verify
kubectl get pvc -n ciagent
```

### 2.6 Setup Monitoring

```bash
# Deploy Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n ciagent

# Deploy Grafana dashboards
kubectl apply -f k8s/grafana-dashboard.yaml

# Access Grafana
kubectl port-forward svc/prometheus-grafana 3000:80 -n ciagent
# Navigate to http://localhost:3000
```

## Part 3: Post-Deployment Verification

### 3.1 Health Checks

```bash
# Test application endpoint
curl http://ci-failure-agent:8000/health

# Check database connectivity
kubectl exec -it deployment/ci-failure-agent -- \
  python -c "from app import db; db.test_connection()"

# Verify logs
kubectl logs -f deployment/ci-failure-agent
```

### 3.2 Smoke Tests

```bash
# Run basic functionality tests
pytest tests/smoke/ -v

# Test API endpoints
http GET http://ci-failure-agent:8000/api/health
http POST http://ci-failure-agent:8000/api/analyze \
  log="ERROR: Build failed"
```

### 3.3 Performance Tests

```bash
# Load testing
locust -f tests/load/locustfile.py \
  --host=http://ci-failure-agent:8000

# Monitor metrics
kubectl top nodes
kubectl top pods -n ciagent
```

## Part 4: CI/CD Automation

### 4.1 GitHub Actions Workflow

File: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Production
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Render
        env:
          RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
        run: |
          curl -X POST https://api.render.com/v1/services/{{SERVICE_ID}}/deploys \
            -H "authorization: Bearer $RENDER_API_KEY"
      - name: Deploy to Kubernetes
        env:
          KUBECONFIG: ${{ secrets.KUBECONFIG }}
        run: |
          kubectl apply -f k8s/
          kubectl rollout status deployment/ci-failure-agent
```

### 4.2 Automatic Scaling

```bash
# Configure autoscaling
kubectl autoscale deployment ci-failure-agent \
  --min=2 --max=10 \
  --cpu-percent=80
```

## Troubleshooting

### Common Issues

**Issue**: Pod CrashLoopBackOff
```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name> --previous
```

**Issue**: Database connection failed
```bash
# Verify credentials
kubectl get secrets database-credentials -o yaml
# Test connection
kubectl exec -it <pod> -- psql -h postgres -U postgres
```

**Issue**: Service unreachable
```bash
# Check service
kubectl get svc -n ciagent
# Check ingress
kubectl describe ingress -n ciagent
# Check DNS
kubectl exec -it <pod> -- nslookup ci-failure-agent
```

## Rollback Procedures

```bash
# Rollback last deployment
kubectl rollout undo deployment/ci-failure-agent

# Check rollout history
kubectl rollout history deployment/ci-failure-agent

# Rollback to specific revision
kubectl rollout undo deployment/ci-failure-agent --to-revision=3
```

## Next Steps

Refer to:
- MONITORING_SETUP.md - Configure monitoring and alerting
- RUNBOOK_OPERATIONS.md - Operational procedures
- DISASTER_RECOVERY.md - Disaster recovery procedures

Version: 1.0
Last Updated: 2025-01-01
