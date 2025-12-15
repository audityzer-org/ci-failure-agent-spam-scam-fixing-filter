# PHASE 1: DETAILED KUBERNETES CLUSTER SETUP

**Timeline**: December 16-27, 2025 | **Priority**: HIGH | **Team**: DevOps

## Executive Summary

Phase 1 establishes the foundation for the entire CI/CD infrastructure using AWS EKS (Elastic Kubernetes Service). This phase includes cluster creation, node configuration, essential add-ons, RBAC, storage, and network policies.

---

## DECISION 1: Cloud Provider Selection ✅ RECOMMENDED: AWS EKS

### Comparison Matrix

| Feature | AWS EKS | Google GKE | Azure AKS |
|---------|---------|-----------|----------|
| Kubernetes Version | 1.28+ | 1.28+ | 1.28+ |
| Cluster Fee | $0.10/hour | Free | Free |
| Node Cost (t3.medium equiv) | $0.0416/hour | $0.0289/hour | Similar |
| Monthly Baseline | ~$73 | ~$0 | ~$0 |
| IAM Integration | Excellent | Good | Good |
| Multi-Region | Native | Native | Native |
| Community Size | Largest | Large | Medium |
| Auto-scaling | Excellent | Excellent | Good |
| Cost Prediction | Easy | Medium | Medium |
| Monitoring | CloudWatch + Prometheus | Stackdriver | Azure Monitor |

**SELECTED: AWS EKS** - Best balance for production systems with strong monitoring & community.

---

## IMPLEMENTATION STEPS

### Step 1: AWS Account & CLI Setup

```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Configure AWS credentials
aws configure
# Enter Access Key, Secret Key, Region: eu-west-1, Output: json

# Verify setup
aws sts get-caller-identity
```

### Step 2: Create EKS Cluster Configuration

Create file: `k8s/eks-cluster.yaml`

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: chatbot-prod
  region: eu-west-1
  version: "1.28"
  tags:
    Environment: production
    Project: ci-failure-agent

iam:
  withOIDC: true
  serviceAccounts:
    - metadata:
        name: aws-load-balancer-controller
        namespace: kube-system
      attachPolicyARNs:
        - arn:aws:iam::aws:policy/ElasticLoadBalancingFullAccess

networking:
  cidr: "10.0.0.0/16"
  nat:
    gateway: "Single"
  publicAccessCidrs:
    - "0.0.0.0/0"
  clusterLogging:
    enableTypes:
      - "api"
      - "audit"
      - "authenticator"
      - "controllerManager"
      - "scheduler"

nodeGroups:
  - name: primary-nodes
    amiFamily: AmazonLinux2
    instanceType: t3.medium
    minSize: 3
    maxSize: 10
    desiredCapacity: 3
    volumeSize: 100
    volumeType: gp3
    volumeEncrypted: true
    labels:
      role: primary
      environment: production
    tags:
      Name: chatbot-primary-node
      ManagedBy: eksctl
    iam:
      withAddonPolicy:
        ebs: true
        efs: true
        albIngress: true
        autoScaler: true
    ssh:
      allow: false

addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: ebs-csi-driver
    version: latest
```

### Step 3: Deploy EKS Cluster

```bash
# Create cluster (15-20 minutes)
eksctl create cluster -f k8s/eks-cluster.yaml

# Update kubeconfig
aws eks update-kubeconfig \
  --region eu-west-1 \
  --name chatbot-prod

# Verify cluster
kubectl cluster-info
kubectl get nodes -o wide
kubectl get all --all-namespaces
```

### Step 4: Install Essential Add-ons

#### AWS Load Balancer Controller

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=chatbot-prod \
  --set serviceAccount.create=true \
  --set serviceAccount.annotations.'eks\.amazonaws\.com/role-arn'=arn:aws:iam::ACCOUNT_ID:role/aws-load-balancer-controller

kubectl -n kube-system get svc
```

#### Metrics Server (for HPA)

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl get deployment metrics-server -n kube-system
```

#### Cluster Autoscaler

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=chatbot-prod \
  --set awsRegion=eu-west-1 \
  --set rbac.serviceAccount.create=true

kubectl -n kube-system get deployment cluster-autoscaler
```

### Step 5: Create Namespaces

```bash
kubectl create namespace production
kubectl create namespace staging
kubectl create namespace monitoring
kubectl create namespace ingress-nginx

kubectl label namespace production name=production
kubectl label namespace staging name=staging
```

### Step 6: Configure RBAC

Create file: `k8s/rbac.yaml`

```yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: chatbot-app
  namespace: production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: chatbot-app
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: chatbot-app
  namespace: production
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: chatbot-app
subjects:
  - kind: ServiceAccount
    name: chatbot-app
    namespace: production
```

```bash
kubectl apply -f k8s/rbac.yaml
```

### Step 7: Storage Configuration

Create file: `k8s/storage.yaml`

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  deleteOnTermination: "true"
allowVolumeExpansion: true
reclaimPolicy: Delete
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-retain
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  deleteOnTermination: "false"
allowVolumeExpansion: true
reclaimPolicy: Retain
```

```bash
kubectl apply -f k8s/storage.yaml
kubectl get storageclass
```

### Step 8: Network Policies

Create file: `k8s/network-policies.yaml`

```yaml
# Default deny ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
---
# Allow from ingress-nginx
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
---
# Allow DNS
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
    - to:
        - podSelector: {}
```

```bash
kubectl apply -f k8s/network-policies.yaml
```

---

## VALIDATION CHECKLIST

✅ = Completed | ⏳ = In Progress | ❌ = Not Started

- [ ] AWS account configured with proper IAM
- [ ] CLI tools installed (aws, kubectl, eksctl, helm)
- [ ] EKS cluster created and running
- [ ] 3+ nodes in Ready state
- [ ] All system pods running in kube-system
- [ ] AWS Load Balancer Controller deployed
- [ ] Metrics Server running
- [ ] Cluster Autoscaler deployed
- [ ] Namespaces created (production, staging, monitoring, ingress-nginx)
- [ ] RBAC configured for chatbot-app
- [ ] StorageClass (ebs-gp3) available
- [ ] Network Policies applied
- [ ] Cluster logging enabled
- [ ] kubectl access verified
- [ ] Cost monitoring enabled in AWS

---

## COST ANALYSIS

**Monthly Estimated Costs** (EU-WEST-1):
- EKS Control Plane: $73
- 3x t3.medium instances @ $0.0416/hour: ~$90
- EBS Storage (3x 100GB gp3): ~$30
- Data Transfer: ~$10
- **Total**: ~$200/month

**Optimization Opportunities**:
- Use Reserved Instances (30% savings)
- Implement Spot Instances for non-critical workloads
- Right-size nodes based on actual usage

---

## TROUBLESHOOTING

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

---

## NEXT PHASE

→ **Phase 2**: Domain Registration & SSL/TLS Setup (Dec 23-27)
