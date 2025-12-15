# IMPLEMENTATION GUIDE: Phase 1 Terraform Infrastructure as Code

## Overview
Повний набір Terraform файлів та скриптів для розгортання AWS EKS кластера, базової інфраструктури та всіх необхідних компонентів для CI/CD Failure Agent системи.

## Architecture
- Region: eu-west-1 (Ireland)
- Cluster: chatbot-prod (EKS)
- Nodes: 3-10 (t3.medium, auto-scaling)
- Namespaces: production, staging, monitoring, ingress-nginx
- Storage: EBS gp3 (100GB per node)
- Networking: VPC 10.0.0.0/16

## Prerequisites
```bash
# Install required tools
# AWS CLI v2, kubectl, eksctl, helm, terraform

aws --version         # AWS CLI 2.x
kubectl version       # Kubernetes 1.28+
eksctl version        # eksctl 0.180+
helm version          # Helm 3.x
terraform -version    # Terraform 1.5+
```

## Quick Start (5 хвилин)

### 1. Configure AWS Credentials
```bash
aws configure
# Enter:
# AWS Access Key ID: YOUR_KEY
# AWS Secret Access Key: YOUR_SECRET
# Default region: eu-west-1
# Default output format: json
```

### 2. Create EKS Cluster
```bash
# eksctl create cluster \\
  --name chatbot-prod \\
  --region eu-west-1 \\
  --nodegroup-name primary-nodes \\
  --node-type t3.medium \\
  --nodes 3 \\
  --nodes-min 3 \\
  --nodes-max 10 \\
  --managed \\
  --enable-ssm

# Time: 15-20 minutes
```

### 3. Verify Cluster
```bash
kubectl cluster-info
kubectl get nodes
kubectl get all --all-namespaces
```

### 4. Install Add-ons
```bash
# AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \\
  -n kube-system \\
  --set clusterName=chatbot-prod

# Metrics Server (для HPA)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Cluster Autoscaler
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \\
  --namespace kube-system \\
  --set autoDiscovery.clusterName=chatbot-prod \\
  --set awsRegion=eu-west-1
```

### 5. Create Namespaces
```bash
kubectl create namespace production
kubectl create namespace staging
kubectl create namespace monitoring
kubectl create namespace ingress-nginx
```

### 6. Configure RBAC
```bash
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/storage.yaml
kubectl apply -f k8s/network-policies.yaml
```

## Complete Deployment Timeline
- **T+0 min**: AWS CLI configuration
- **T+5 min**: EKS cluster creation started
- **T+25 min**: Cluster operational, nodes ready
- **T+30 min**: Add-ons installed
- **T+35 min**: Namespaces and RBAC configured
- **T+40 min**: All components ready for Phase 2

## Verification Checklist
- [ ] Cluster running: `kubectl cluster-info`
- [ ] 3+ nodes Ready: `kubectl get nodes`
- [ ] All pods running: `kubectl get all --all-namespaces`
- [ ] Load Balancer Controller deployed
- [ ] Metrics Server operational
- [ ] Cluster Autoscaler active
- [ ] Namespaces created
- [ ] RBAC configured
- [ ] StorageClass available
- [ ] Network policies applied

## Troubleshooting

### Cluster not responding
```bash
eksctl get cluster --name chatbot-prod
eksctl describe cluster --name chatbot-prod
```

### Nodes not joining
```bash
kubectl describe nodes
kubectl logs -n kube-system -l k8s-app=aws-node
```

### Storage issues
```bash
kubectl get pvc --all-namespaces
kubectl describe pvc -n production
```

## Cost Monitoring
```bash
# Enable CloudWatch monitoring
aws eks describe-cluster --name chatbot-prod

# Monthly estimate: ~$200
# - EKS Control Plane: $73
# - 3x t3.medium: ~$90
# - Storage (300GB): ~$30
# - Data transfer: ~$10
```

## Next Steps
→ Phase 2: Domain Registration & SSL/TLS Setup (Dec 23-27, 2025)

## Support
- Documentation: PHASE_1_DETAILED_KUBERNETES_SETUP.md
- Deployment Guide: DEPLOYMENT_GUIDE.md
- Runbook: RUNBOOK_OPERATIONS.md
