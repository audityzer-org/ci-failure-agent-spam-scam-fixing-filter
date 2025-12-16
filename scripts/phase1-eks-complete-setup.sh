#!/bin/bash
# Phase 1: Complete AWS EKS Cluster Deployment with IAM Roles & Security
# This script creates a production-ready EKS cluster with all necessary components

set -e  # Exit on error

# Configuration Variables
CLUSTER_NAME=${CLUSTER_NAME:-"ci-failure-agent"}
REGION=${AWS_REGION:-"us-east-1"}
NODE_TYPE=${NODE_TYPE:-"t3.medium"}
NODE_COUNT=${NODE_COUNT:-3}
KUBERNETES_VERSION=${K8S_VERSION:-"1.28"}
DOMAIN=${DOMAIN:-"ci-failure-agent.tech"}

echo "========================================"
echo "Phase 1: AWS EKS Cluster Setup"
echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"
echo "Node Type: $NODE_TYPE (Count: $NODE_COUNT)"
echo "========================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "[1/8] Checking prerequisites..."
if ! command_exists aws; then
    echo "ERROR: AWS CLI not installed. Install from: https://aws.amazon.com/cli/"
    exit 1
fi

if ! command_exists eksctl; then
    echo "Installing eksctl..."
    curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
    sudo mv /tmp/eksctl /usr/local/bin
fi

if ! command_exists kubectl; then
    echo "Installing kubectl..."
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
fi

# Verify AWS credentials
echo "[2/8] Verifying AWS credentials..."
aws sts get-caller-identity || { echo "ERROR: AWS credentials not configured"; exit 1; }

# Create EKS Cluster
echo "[3/8] Creating EKS cluster: $CLUSTER_NAME..."
eksctl create cluster \
  --name "$CLUSTER_NAME" \
  --region "$REGION" \
  --node-type "$NODE_TYPE" \
  --nodes "$NODE_COUNT" \
  --version "$KUBERNETES_VERSION" \
  --vpc-cidr "10.0.0.0/16" \
  --with-oidc \
  --enable-ssm

echo "Cluster created successfully!"

# Configure kubectl context
echo "[4/8] Configuring kubectl..."
aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER_NAME"
echo "kubectl configured. Testing connection..."
kubectl cluster-info

# Create namespaces
echo "[5/8] Creating Kubernetes namespaces..."
kubectl create namespace production --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace staging --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -

# Configure IAM Roles for Pod Access
echo "[6/8] Setting up IAM roles for pod access..."
OIDC_ID=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" --query "cluster.identity.oidc.issuer" --output text | cut -d '/' -f 5)
echo "OIDC ID: $OIDC_ID"

# Create IAM policy for application
echo "Creating IAM policy..."
cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):oidc-provider/oidc.eks.${REGION}.amazonaws.com/id/${OIDC_ID}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.${REGION}.amazonaws.com/id/${OIDC_ID}:sub": "system:serviceaccount:production:app-sa"
        }
      }
    }
  ]
}
EOF

aws iam create-role --role-name "${CLUSTER_NAME}-app-role" \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --description "Role for CI Failure Agent application" 2>/dev/null || echo "Role already exists"

# Attach policies
aws iam attach-role-policy --role-name "${CLUSTER_NAME}-app-role" \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy || true

# Create service account
echo "Creating Kubernetes service account..."
kubectl create serviceaccount app-sa -n production --dry-run=client -o yaml | kubectl apply -f -

# Annotate service account with IAM role
kubectl annotate serviceaccount app-sa \
  -n production \
  eks.amazonaws.com/role-arn=arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/${CLUSTER_NAME}-app-role \
  --overwrite=true

# Configure Security Groups
echo "[7/8] Configuring security groups..."
SEC_GROUP_ID=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" --query 'cluster.resourcesVpcConfig.securityGroupIds[0]' --output text)
echo "Security Group ID: $SEC_GROUP_ID"

# Allow ingress traffic on port 80 and 443
aws ec2 authorize-security-group-ingress \
  --group-id "$SEC_GROUP_ID" \
  --protocol tcp --port 80 --cidr 0.0.0.0/0 2>/dev/null || echo "Port 80 already open"

aws ec2 authorize-security-group-ingress \
  --group-id "$SEC_GROUP_ID" \
  --protocol tcp --port 443 --cidr 0.0.0.0/0 2>/dev/null || echo "Port 443 already open"

# Enable auto-scaling
echo "[8/8] Enabling auto-scaling..."
eksctl create addon --name aws-ebs-csi-driver --cluster "$CLUSTER_NAME" --region "$REGION" 2>/dev/null || echo "EBS driver addon already exists"
eksctl create addon --name vpc-cni --cluster "$CLUSTER_NAME" --region "$REGION" 2>/dev/null || echo "VPC CNI addon already exists"

# Verify cluster setup
echo "\n========================================"
echo "EKS Cluster Setup Complete!"
echo "========================================\n"

echo "Cluster Status:"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" --query 'cluster.status' --output text

echo "\nCluster Nodes:"
kubectl get nodes -o wide

echo "\nNamespaces:"
kubectl get namespaces

echo "\nCluster Info:"
echo "Name: $CLUSTER_NAME"
echo "Region: $REGION"
echo "Endpoint: $(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" --query 'cluster.endpoint' --output text)"
echo "OIDC ID: $OIDC_ID"
echo "\nNext steps:"
echo "1. Deploy cert-manager: ./phase2-cert-manager-setup.sh"
echo "2. Deploy application: kubectl apply -f k8s/deployment.yaml -n production"
echo "3. Configure DNS for domain: $DOMAIN"
