# Phase 1 Implementation Guide: Kubernetes Cluster Planning & Setup

## Overview
This guide provides step-by-step instructions for implementing Phase 1 of the CI Failure Agent deployment, focusing on Kubernetes cluster planning and infrastructure setup.

**Timeline**: December 16-27, 2025 (2 weeks)
**Status**: 🔄 IN PROGRESS
**Priority**: HIGH

---

## Phase 1 Objectives

1. **Cloud Provider Selection** - Choose AWS EKS, Google GKE, or Azure AKS
2. **Kubernetes Cluster Setup** - Create a production-grade cluster with 3+ nodes
3. **Network Configuration** - Set up VPC, subnets, and security groups
4. **IAM/RBAC Setup** - Configure authentication and role-based access control
5. **Auto-scaling Configuration** - Enable horizontal pod and node scaling

---

## Pre-Requisites

- [ ] AWS/GCP/Azure account with appropriate permissions
- [ ] `kubectl` installed locally (v1.28 or later)
- [ ] `helm` package manager installed (v3.12 or later)
- [ ] `terraform` or cloud-specific CLI tools installed
- [ ] Git repository access with write permissions
- [ ] Team members with DevOps/SRE experience assigned

---

## Step 1: Cloud Provider Decision (Decision Due: Dec 15)

### Comparison Matrix

| Criteria | AWS EKS | Google GKE | Azure AKS |
|----------|---------|-----------|----------|
| Cost Efficiency | $0.10/hour | $0.15/hour | $0.15/hour |
| Kubernetes Version | 1.28.x | 1.28.x | 1.28.x |
| Auto-scaling | Native HPA + Karpenter | Native GKE Autopilot | Native KEDA |
| Managed Services | RDS, ElastiCache, S3 | Cloud SQL, Cloud Cache, GCS | Azure Database, Azure Cache |
| Compliance | SOC2, ISO 27001 | SOC2, ISO 27001 | SOC2, ISO 27001 |
| Support Level | 24/7 Enterprise | 24/7 Enterprise | 24/7 Enterprise |

### RECOMMENDATION: AWS EKS
**Rationale**: 
- Best integration with existing Terraform infrastructure
- RDS support for PostgreSQL already configured
- Cost-effective for predicted workload
- Mature managed Kubernetes service

---

## Step 2: AWS EKS Cluster Setup

### 2.1 Pre-Flight Checks

```bash
# Verify AWS CLI installation and credentials
aws sts get-caller-identity

# Set AWS region (recommended: us-east-1)
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Verify Kubernetes CLI tools
kubectl version --client
helm version
```

### 2.2 Create EKS Cluster using Terraform

**File**: `terraform/eks_cluster.tf`

```hcl
# EKS Cluster Definition
resource "aws_eks_cluster" "ci_failure_agent" {
  name     = "ci-failure-agent-eks"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.28"

  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    security_group_ids      = [aws_security_group.eks_cluster_sg.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller
  ]

  tags = {
    Name        = "ci-failure-agent-eks"
    Environment = "production"
    Phase       = "1"
  }
}

# EKS Node Group
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.ci_failure_agent.name
  node_group_name = "ci-failure-agent-nodes"
  node_role_arn   = aws_iam_role.node_role.arn
  subnet_ids      = var.private_subnet_ids
  version         = "1.28"

  scaling_config {
    desired_size = 3
    max_size     = 10
    min_size     = 2
  }

  instance_types = ["t3.medium"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy
  ]

  tags = {
    Name        = "ci-failure-agent-nodes"
    Environment = "production"
  }
}
```

### 2.3 Deploy Cluster

```bash
cd terraform

# Initialize Terraform
terraform init \
  -backend-config="bucket=ci-failure-agent-tfstate" \
  -backend-config="region=us-east-1"

# Plan deployment
terraform plan -out=eks.tfplan

# Apply configuration
terraform apply eks.tfplan

# Output cluster endpoint
terraform output -raw eks_cluster_endpoint
```

### 2.4 Configure kubectl

```bash
# Update kubeconfig with EKS cluster info
aws eks update-kubeconfig \
  --region us-east-1 \
  --name ci-failure-agent-eks

# Verify connectivity
kubectl get nodes
kubectl get pods -A
```

---

## Step 3: VPC & Network Configuration

### 3.1 VPC Architecture

```
VPC: 10.0.0.0/16
├── Public Subnets (NAT Gateway ingress)
│   ├── us-east-1a: 10.0.1.0/24
│   ├── us-east-1b: 10.0.2.0/24
│   └── us-east-1c: 10.0.3.0/24
├── Private Subnets (EKS Nodes)
│   ├── us-east-1a: 10.0.11.0/24
│   ├── us-east-1b: 10.0.12.0/24
│   └── us-east-1c: 10.0.13.0/24
└── Database Subnets
    ├── us-east-1a: 10.0.21.0/24
    └── us-east-1b: 10.0.22.0/24
```

### 3.2 Security Groups

```bash
# EKS Cluster Security Group
aws ec2 create-security-group \
  --group-name eks-cluster-sg \
  --description "Security group for EKS cluster" \
  --vpc-id <VPC_ID>

# Allow communication between nodes
aws ec2 authorize-security-group-ingress \
  --group-id <SG_ID> \
  --protocol all \
  --port -1 \
  --source-group <SG_ID>

# Allow ingress from internet (port 443 for API)
aws ec2 authorize-security-group-ingress \
  --group-id <SG_ID> \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

---

## Step 4: IAM & RBAC Configuration

### 4.1 EKS Service Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### 4.2 Node IAM Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### 4.3 RBAC Setup in Kubernetes

```yaml
# File: k8s/rbac-config.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-failure-agent-sa
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ci-failure-agent-role
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/logs"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["get", "list"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: ci-failure-agent-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: ci-failure-agent-role
subjects:
  - kind: ServiceAccount
    name: ci-failure-agent-sa
    namespace: default
```

---

## Step 5: Auto-scaling Configuration

### 5.1 Horizontal Pod Autoscaler (HPA)

```yaml
# File: k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ci-failure-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ci-failure-agent
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### 5.2 Cluster Autoscaler Setup

```bash
# Install Cluster Autoscaler via Helm
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update

helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set awsRegion=us-east-1 \
  --set autoDiscovery.clusterName=ci-failure-agent-eks \
  --set rbac.serviceAccount.name=cluster-autoscaler
```

---

## Step 6: Verification & Testing

### 6.1 Cluster Health Check

```bash
# Check cluster status
kubectl get nodes
kubectl get pods -A
kubectl get svc -A

# Verify cluster components
kubectl get deployment -n kube-system
kubectl get daemonset -n kube-system
```

### 6.2 Deploy Test Application

```yaml
# File: k8s/test-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: test-app
  template:
    metadata:
      labels:
        app: test-app
    spec:
      containers:
        - name: test-app
          image: nginx:latest
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

```bash
# Deploy test application
kubectl apply -f k8s/test-deployment.yaml

# Verify deployment
kubectl get pods -l app=test-app
kubectl logs deployment/test-app
```

---

## Deliverables Checklist

- [ ] Cloud provider decision documented and approved
- [ ] EKS cluster deployed with 3 master nodes
- [ ] VPC with public/private subnets across 3 AZs
- [ ] Security groups configured with least-privilege rules
- [ ] IAM roles and RBAC policies implemented
- [ ] Horizontal and Cluster autoscaling configured
- [ ] kubectl configured and cluster verified operational
- [ ] Test application deployed and running
- [ ] Monitoring of cluster health initiated
- [ ] Documentation updated with cluster endpoints

---

## Next Steps

→ **Phase 2**: Domain & SSL/TLS Configuration (Starting Dec 23)

---

**Document Version**: 1.0
**Created**: December 14, 2025
**Last Updated**: December 14, 2025
**Status**: Active
**Owner**: DevOps Team
