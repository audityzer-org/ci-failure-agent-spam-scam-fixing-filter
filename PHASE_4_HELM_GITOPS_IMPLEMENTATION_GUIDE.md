# Phase 4 Implementation Guide: Helm Charts & GitOps Deployment

## Overview
Phase 4 focuses on creating production-grade Helm charts and implementing GitOps workflows using ArgoCD for automated, declarative deployments.

**Timeline**: January 6-10, 2026 (1 week)
**Status**: 📅 SCHEDULED
**Priority**: HIGH
**Dependencies**: Phases 1-3 complete

---

## Phase 4 Objectives

1. **Helm Chart Creation** - Package application with Helm
2. **ArgoCD Installation** - Deploy GitOps controller
3. **Environment Configuration** - Dev, staging, production values
4. **Automated Deployments** - Git-driven deployments
5. **Rollback Procedures** - Safe version management

---

## Step 1: Create Helm Chart

### 1.1 Chart Structure

```bash
helm create ci-failure-agent
cd ci-failure-agent/
```

**Directory Structure**:
```
ci-failure-agent/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-staging.yaml
├── values-prod.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   └── hpa.yaml
└─┠ README.md
```

### 1.2 Chart.yaml

```yaml
apiVersion: v2
name: ci-failure-agent
description: CI Failure Agent ML-powered microservice
type: application
version: 1.1.0
appVersion: "1.0.0"
keywords:
  - ci
  - failure
  - agent
maintainers:
  - name: DevOps Team
home: https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter
sources:
  - https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter
```

### 1.3 Values.yaml (Production Template)

```yaml
replicaCount: 3
image:
  repository: audityzer-org/ci-failure-agent
  pullPolicy: IfNotPresent
  tag: "1.0.0"

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: ci-failure-agent.io
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: ci-failure-agent-tls
      hosts:
        - ci-failure-agent.io

resources:
  limits:
    cpu: 1000m
    memory: 512Mi
  requests:
    cpu: 500m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

---

## Step 2: Install ArgoCD

### 2.1 Install ArgoCD

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s
```

### 2.2 Access ArgoCD UI

```bash
# Port forward
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get initial password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Access at https://localhost:8080
# Username: admin
```

---

## Step 3: GitOps Configuration

### 3.1 ArgoCD Application Manifest

**File**: `argocd-app.yaml`

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ci-failure-agent
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter
    targetRevision: main
    path: helm/ci-failure-agent
    helm:
      releaseName: ci-failure-agent
      values: |
        replicaCount: 3
        image:
          tag: "1.0.0"
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

```bash
# Apply ArgoCD application
kubectl apply -f argocd-app.yaml

# Check sync status
kubectl get application ci-failure-agent -n argocd
argocd app get ci-failure-agent
```

---

## Step 4: Deployment Validation

```bash
# Verify Helm chart
helm lint ./ci-failure-agent

# Dry run deployment
helm template ci-failure-agent ./ci-failure-agent -f values-prod.yaml

# Manual deployment test
helm install ci-failure-agent ./ci-failure-agent \
  -f values-prod.yaml \
  --namespace default
```

---

## Deliverables Checklist

- [ ] Helm chart created and validated
- [ ] Environment-specific values files (dev, staging, prod)
- [ ] ArgoCD installed and operational
- [ ] GitOps application configured
- [ ] Git-driven deployments working
- [ ] Automated sync enabled
- [ ] Rollback procedures tested
- [ ] Documentation complete

---

## Next Steps

→ **Phase 5**: Database & Disaster Recovery (Starting Jan 13)

---

**Document Version**: 1.0
**Created**: December 14, 2025
**Owner**: Platform Engineering Team
