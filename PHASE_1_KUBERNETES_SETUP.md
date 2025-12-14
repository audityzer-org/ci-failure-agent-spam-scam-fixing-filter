# Phase 1: Kubernetes Cluster Setup & Deployment

## Timeline
**Start Date**: December 16, 2025
**End Date**: December 27, 2025
**Duration**: 12 days (2 weeks)

## Overview
This phase focuses on setting up a production-ready Kubernetes cluster and deploying the CI Failure Agent application for enterprise-scale operation.

---

## Step 1: Cloud Provider Selection

### Decision Point
**Question**: Which cloud provider should we use?
- **AWS EKS** (Amazon Elastic Kubernetes Service)
- **Google GKE** (Google Kubernetes Engine)
- **Azure AKS** (Azure Kubernetes Service)

### Recommendation
**AWS EKS** is recommended for this project based on:
- Cost-effectiveness for small to medium workloads
- Robust integration with AWS services
- Strong community support
- Existing AWS infrastructure familiarity

### Decision Deadline
**December 15, 2025** (TOMORROW)

---

## Step 2: AWS EKS Cluster Setup

### Prerequisites
Before starting cluster creation, ensure you have:

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
   ```bash
   # Install AWS CLI v2
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   
   # Verify installation
   aws --version
   
   # Configure credentials
   aws configure
   ```

3. **kubectl** installed
   ```bash
   # Install kubectl
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   
   # Verify installation
   kubectl version --client
   ```

4. **eksctl** installed (EKS management tool)
   ```bash
   # Install eksctl
   curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
   sudo mv /tmp/eksctl /usr/local/bin/
   
   # Verify installation
   eksctl version
   ```

### Cluster Creation

#### Option A: Quick Setup with eksctl (RECOMMENDED)

```bash
# Create EKS cluster with default configuration
eksctl create cluster \
  --name ci-failure-agent \
  --region us-east-1 \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5 \
  --with-oidc \
  --ssh-public-key your-key-name
```

**Command Breakdown**:
- `--name`: Cluster name
- `--region`: AWS region (us-east-1, eu-west-1, ap-southeast-1 options)
- `--node-type`: EC2 instance type (t3.medium = 2 CPU, 4GB RAM)
- `--nodes`: Initial number of worker nodes
- `--nodes-min/max`: Auto-scaling range
- `--with-oidc`: Enable OIDC provider for pod identity
- `--ssh-public-key`: For SSH access to nodes

**Estimated Time**: 15-20 minutes

#### Option B: Advanced Setup with CloudFormation

For more control, use AWS CloudFormation templates:

```bash
# Create cluster with IAM roles, VPC, security groups
eksctl create cluster -f cluster-config.yaml
```

**cluster-config.yaml** example:
```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: ci-failure-agent
  region: us-east-1

nodeGroups:
  - name: ng-primary
    desiredCapacity: 3
    minSize: 2
    maxSize: 5
    instanceType: t3.medium
    ssh:
      publicKeyName: your-key-name

iam:
  withOIDC: true
```

### Verify Cluster Creation

```bash
# Check cluster status
eksctl get clusters

# Get cluster information
aws eks describe-cluster --name ci-failure-agent --region us-east-1

# Configure kubectl
aws eks update-kubeconfig --name ci-failure-agent --region us-east-1

# Verify nodes are ready
kubectl get nodes
kubectl get nodes -o wide

# Check node status
kubectl describe nodes
```

---

## Step 3: Configure IAM Roles and RBAC

### Service Account Setup for Pod Identity

```bash
# Create namespace for CI Failure Agent
kubectl create namespace ci-failure-agent

# Create service account
kubectl create serviceaccount ci-failure-agent-sa -n ci-failure-agent

# Create IAM policy for the service
cat <<EOF > ci-failure-agent-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::ci-failure-agent-*",
        "arn:aws:s3:::ci-failure-agent-*/*"
      ]
    }
  ]
}
EOF

# Create IAM role
aws iam create-role \
  --role-name ci-failure-agent-role \
  --assume-role-policy-document file://trust-policy.json
```

### RBAC Configuration

```bash
# Create role for pod
kubectl create role ci-failure-agent-role \
  --verb=get,list,watch \
  --resource=pods \
  -n ci-failure-agent

# Create role binding
kubectl create rolebinding ci-failure-agent-binding \
  --role=ci-failure-agent-role \
  --serviceaccount=ci-failure-agent:ci-failure-agent-sa \
  -n ci-failure-agent
```

---

## Step 4: Install Essential Add-ons

### AWS Load Balancer Controller

```bash
# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=ci-failure-agent
```

### Container Image Registry (ECR)

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name ci-failure-agent \
  --region us-east-1

# Get login token
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.us-east-1.amazonaws.com
```

### Cluster Autoscaler

```bash
# Deploy Cluster Autoscaler
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml
```

---

## Step 5: Deploy CI Failure Agent

### Build and Push Docker Image

```bash
# Build Docker image
docker build -t ci-failure-agent:v1.0.0 .

# Tag for ECR
docker tag ci-failure-agent:v1.0.0 <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/ci-failure-agent:v1.0.0

# Push to ECR
docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/ci-failure-agent:v1.0.0
```

### Deploy to Kubernetes

```bash
# Update deployment image in k8s/deployment.yaml
sed -i 's|IMAGE_URL|<your-account-id>.dkr.ecr.us-east-1.amazonaws.com/ci-failure-agent:v1.0.0|g' k8s/deployment.yaml

# Apply Kubernetes manifests
kubectl apply -f k8s/deployment.yaml -n ci-failure-agent
kubectl apply -f k8s/service.yaml -n ci-failure-agent
kubectl apply -f k8s/ingress-storage-monitoring.yaml -n ci-failure-agent

# Verify deployment
kubectl get deployments -n ci-failure-agent
kubectl get pods -n ci-failure-agent
kubectl logs -f deployment/ci-failure-agent -n ci-failure-agent
```

---

## Step 6: Configure Auto-Scaling

### Horizontal Pod Autoscaler (HPA)

```bash
# Create HPA
kubectl autoscale deployment ci-failure-agent \
  --min=2 \
  --max=10 \
  --cpu-percent=70 \
  -n ci-failure-agent

# Check HPA status
kubectl get hpa -n ci-failure-agent
```

### Vertical Pod Autoscaler (VPA)

```bash
# Install VPA
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm install vpa fairwinds-stable/vpa

# Create VPA resource
cat <<EOF | kubectl apply -f -
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: ci-failure-agent-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ci-failure-agent
  updatePolicy:
    updateMode: Auto
EOF
```

---

## Success Criteria

- ✅ Kubernetes cluster created with 3+ nodes
- ✅ All nodes in "Ready" state
- ✅ kubectl configured and working
- ✅ CI Failure Agent pods deployed and running
- ✅ Service accessible via load balancer
- ✅ Auto-scaling configured and tested
- ✅ All add-ons installed and operational

## Verification Commands

```bash
# Verify cluster
kubectl get nodes
kubectl get namespaces
kubectl get all -n ci-failure-agent

# Check pod resources
kubectl top nodes
kubectl top pods -n ci-failure-agent

# Verify load balancer
kubectl get svc -n ci-failure-agent
kubectl describe svc ci-failure-agent-service -n ci-failure-agent
```

## Next Phase
Once cluster is running, proceed to **Phase 2: Domain & SSL/TLS Configuration** (December 23-27, 2025)

---

**Document Version**: 1.0
**Last Updated**: December 14, 2025, 10:30 AM EET
**Status**: Ready for Implementation
**Owner**: DevOps Team
