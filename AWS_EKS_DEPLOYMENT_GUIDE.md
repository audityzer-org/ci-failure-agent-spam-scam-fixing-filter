# AWS EKS Cluster Deployment Guide
## Complete Infrastructure Setup for auditorsec.com & audityzer.com

### Overview
This guide provides comprehensive instructions for deploying a production-ready Kubernetes cluster on AWS EKS with support for CI/CD failure agent infrastructure, government agency auditing, and energy sector monitoring systems.

### Architecture
- **Cluster**: AWS EKS (Elastic Kubernetes Service)
- **Region**: us-east-1 (configurable)
- **Nodes**: 3 worker nodes (t3.medium/large, auto-scaling 2-10)
- **Network**: Multi-AZ deployment with public/private subnets
- **Domains**: auditorsec.com, audityzer.com

### Prerequisites

1. **AWS Account**
   - Active AWS account with appropriate permissions
   - IAM user with EC2, EKS, VPC, and IAM permissions
   - AWS CLI v2 configured with credentials

2. **Local Tools**
   ```bash
   # Install Terraform
   curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
   sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
   sudo apt-get update && sudo apt-get install terraform
   
   # Install kubectl
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
   
   # Install AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

3. **AWS Credentials**
   ```bash
   aws configure
   # Enter AWS Access Key ID
   # Enter AWS Secret Access Key
   # Default region: us-east-1
   # Default output format: json
   ```

### Deployment Steps

#### 1. Clone Repository
```bash
git clone https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter.git
cd ci-failure-agent-spam-scam-fixing-filter/terraform
```

#### 2. Review Configuration
```bash
# Check current variables
cat terraform.tfvars

# Key configuration:
# - aws_region: us-east-1
# - cluster_name: ci-failure-agent-cluster
# - kubernetes_version: 1.28
# - Nodes: 3 desired, 2 min, 10 max
# - Instance types: t3.medium, t3.large
```

#### 3. Initialize Terraform
```bash
terraform init

# This will:
# - Download AWS and Kubernetes providers
# - Initialize .terraform directory
# - Create terraform.tfstate
```

#### 4. Validate Configuration
```bash
terraform validate

# Checks syntax and configuration consistency
```

#### 5. Review Plan
```bash
terraform plan -out=tfplan

# Review proposed changes:
# - VPC with subnets across availability zones
# - Internet Gateway and NAT Gateways
# - EKS cluster with control plane
# - 3 worker nodes in private subnets
# - Security groups and IAM roles
```

#### 6. Apply Configuration
```bash
terraform apply tfplan

# This will create:
# - VPC infrastructure (~5 minutes)
# - EKS cluster (~15 minutes)
# - Worker nodes (~10 minutes)
# Total time: ~30 minutes
```

#### 7. Configure kubectl
```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name ci-failure-agent-cluster

# Verify connection
kubectl get nodes
# Output should show 3 nodes in Ready state
```

### Post-Deployment Configuration

#### 1. Install CoreDNS
```bash
kubectl apply -f https://raw.githubusercontent.com/coredns/deployment/master/kubernetes/coredns.yaml.sed
```

#### 2. Install Metrics Server
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify
kubectl get deployment metrics-server -n kube-system
```

#### 3. Install Network Policy Controller (Calico)
```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/tigera-operator.yaml
```

#### 4. Install Load Balancer Controller
```bash
# Create IAM policy
wget https://github.com/kubernetes-sigs/aws-load-balancer-controller/releases/download/v2.6.0/iam_policy.json

aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam_policy.json

# Install controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=ci-failure-agent-cluster
```

#### 5. Configure RBAC
```bash
kubectl create namespace ci-failure-agent
kubectl create namespace monitoring
kubectl create namespace logging
```

#### 6. Set Up Persistent Storage
```bash
# EBS CSI Driver
helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
  -n kube-system
```

### Deploy Applications

#### 1. CI/CD Failure Agent
```bash
kubectl apply -f k8s/ci-failure-agent-deployment.yaml
kubectl apply -f k8s/ci-failure-agent-service.yaml
```

#### 2. Domain Configuration
```bash
# Get Load Balancer Endpoint
kubectl get svc -n ci-failure-agent

# Configure DNS for auditorsec.com and audityzer.com
# Point CNAME records to ALB endpoint
```

#### 3. TLS Certificate Setup
```bash
# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  -n cert-manager \
  --create-namespace

# Create certificate for domains
kubectl apply -f k8s/certificate-auditorsec.yaml
kubectl apply -f k8s/certificate-audityzer.yaml
```

### Monitoring & Logging

#### 1. CloudWatch Integration
```bash
# EKS logs are automatically sent to CloudWatch
aws logs describe-log-groups --query 'logGroups[*].logGroupName' | grep /aws/eks/
```

#### 2. Prometheus & Grafana
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring
```

#### 3. ELK Stack (Elasticsearch, Logstash, Kibana)
```bash
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch -n logging
helm install kibana elastic/kibana -n logging
```

### Security Best Practices

1. **Network Security**
   - Use security groups to restrict traffic
   - Enable VPC Flow Logs
   - Use private subnets for worker nodes

2. **RBAC**
   - Implement least privilege access
   - Use service accounts for applications
   - Regular role audits

3. **Secrets Management**
   - Use AWS Secrets Manager
   - Enable encryption at rest
   - Rotate credentials regularly

4. **Container Security**
   - Scan images for vulnerabilities
   - Use image pull secrets
   - Pod security policies

### Scaling Configuration

#### Horizontal Pod Autoscaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ci-failure-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ci-failure-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

#### Cluster Autoscaling
```bash
# Already configured in Terraform
# Node group auto-scaling: 2-10 nodes
# Automatically scales based on pod requirements
```

### Backup & Disaster Recovery

#### 1. etcd Backup
```bash
# Enable EKS managed backup
aws eks update-cluster-config \
  --name ci-failure-agent-cluster \
  --logging '{{"clusterLogging":[{{"enabled":true,"types":["api","audit","authenticator","controllerManager","scheduler"]}}]}}'
```

#### 2. Persistent Volume Snapshots
```bash
# Use AWS EBS snapshots for PV backup
aws ec2 create-snapshot --volume-id vol-xxxxx
```

### Cost Optimization

1. **Spot Instances** (30-90% discount)
   ```bash
   # Configure in terraform for non-critical workloads
   capacity_type = "SPOT"
   ```

2. **Reserved Instances**
   - Commit to 1-3 year terms
   - Up to 72% savings

3. **Right-Sizing**
   - Monitor CloudWatch metrics
   - Adjust instance types as needed

### Troubleshooting

#### Cluster Not Ready
```bash
# Check cluster status
aws eks describe-cluster --name ci-failure-agent-cluster

# Check control plane logs
aws logs tail /aws/eks/ci-failure-agent-cluster/cluster --follow
```

#### Nodes Not Joining
```bash
# Check node logs
kubectl describe node <node-name>
kubectl logs -n kube-system kubelet
```

#### Pod Networking Issues
```bash
# Verify CNI
kubectl get daemonset -n kube-system
kubectl logs -n kube-system aws-node-xxxxx
```

### Cleanup

#### Destroy Infrastructure
```bash
# Remove all applications first
kubectl delete namespace ci-failure-agent monitoring logging

# Destroy Terraform resources
terraform destroy

# Confirm to proceed with deletion
```

### Additional Resources

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/)
- [Best Practices Guide](https://aws.amazon.com/articles/)

### Support

For issues or questions:
- Check logs: `kubectl logs <pod-name>`
- Review events: `kubectl get events --all-namespaces`
- Contact AWS support or check documentation

---

**Last Updated**: 2024
**Kubernetes Version**: 1.28
**Terraform Version**: >= 1.0
**AWS Provider Version**: >= 5.0
