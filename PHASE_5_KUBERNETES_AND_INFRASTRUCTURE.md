# Phase 5: Kubernetes and Infrastructure Management

## Overview

Phase 5 focuses on enterprise-grade infrastructure deployment using Kubernetes, including multi-region deployment, auto-scaling, disaster recovery, and advanced monitoring.

## Table of Contents

1. [Kubernetes Cluster Setup](#kubernetes-cluster-setup)
2. [Service Deployment](#service-deployment)
3. [Auto-Scaling Configuration](#auto-scaling-configuration)
4. [Multi-Region Deployment](#multi-region-deployment)
5. [Disaster Recovery](#disaster-recovery)
6. [Performance Optimization](#performance-optimization)
7. [Cost Optimization](#cost-optimization)

---

## Kubernetes Cluster Setup

### Infrastructure as Code (Terraform)

Use Terraform for reproducible infrastructure:

```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

### EKS Cluster Creation

**terraform/main.tf:**
```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.0"

  cluster_name    = "ci-failure-agent"
  cluster_version = "1.27"

  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true

  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.private[*].id

  eks_managed_node_group_defaults = {
    instance_types = ["t3.medium"]
  }

  eks_managed_node_groups = {
    general = {
      min_size     = 3
      max_size     = 10
      desired_size = 5
    }
  }
}
```

### RBAC Configuration

```bash
# Create service account
kubectl create serviceaccount ci-failure-agent -n production

# Create ClusterRole for deployments
kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ci-failure-agent
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list"]
EOF
```

---

## Service Deployment

### Kubernetes Deployment Manifest

**k8s/deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ci-failure-agent
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ci-failure-agent
  template:
    metadata:
      labels:
        app: ci-failure-agent
    spec:
      serviceAccountName: ci-failure-agent
      containers:
      - name: ci-failure-agent
        image: audityzer/ci-failure-agent:1.0.0
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: config
          mountPath: /app/config
      volumes:
      - name: config
        configMap:
          name: ci-failure-agent-config
```

### Service Manifest

**k8s/service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ci-failure-agent
  namespace: production
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  selector:
    app: ci-failure-agent
```

### ConfigMap

**k8s/configmap.yaml:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ci-failure-agent-config
  namespace: production
data:
  config.yaml: |
    server:
      host: 0.0.0.0
      port: 8000
      workers: 4
    database:
      pool_size: 20
      timeout: 30
    task_queue:
      max_workers: 10
      timeout: 300
```

### Deployment Commands

```bash
# Create namespace
kubectl create namespace production

# Apply manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml

# Verify deployment
kubectl get pods -n production
kubectl get svc -n production

# Check logs
kubectl logs -f -n production -l app=ci-failure-agent
```

---

## Auto-Scaling Configuration

### Horizontal Pod Autoscaler (HPA)

**k8s/hpa.yaml:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ci-failure-agent-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ci-failure-agent
  minReplicas: 3
  maxReplicas: 20
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
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

### Cluster Autoscaler

```bash
# Install Cluster Autoscaler
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=ci-failure-agent \
  --set awsRegion=us-east-1
```

---

## Multi-Region Deployment

### Primary and Secondary Regions

**terraform/multi-region.tf:**
```hcl
# Primary Region (us-east-1)
module "eks_primary" {
  source = "./modules/eks"
  
  cluster_name = "ci-failure-agent-primary"
  region       = "us-east-1"
  node_count   = 5
}

# Secondary Region (eu-west-1)
module "eks_secondary" {
  source = "./modules/eks"
  
  cluster_name = "ci-failure-agent-secondary"
  region       = "eu-west-1"
  node_count   = 3
}
```

### DNS Failover with Route 53

```hcl
resource "aws_route53_record" "failover_primary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.audityzer.com"
  type    = "A"
  alias {
    name    = module.eks_primary.load_balancer_dns
    zone_id = module.eks_primary.zone_id
    evaluate_target_health = true
  }
  failover_routing_policy {
    type = "PRIMARY"
  }
}

resource "aws_route53_record" "failover_secondary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.audityzer.com"
  type    = "A"
  alias {
    name    = module.eks_secondary.load_balancer_dns
    zone_id = module.eks_secondary.zone_id
    evaluate_target_health = true
  }
  failover_routing_policy {
    type = "SECONDARY"
  }
}
```

---

## Disaster Recovery

### Backup Strategy

```bash
# Install Velero for cluster backups
helm repo add vmware-tanzu https://vmware-tanzu.github.io/helm-charts
helm install velero vmware-tanzu/velero \
  --namespace velero \
  --create-namespace \
  --set configuration.backupStorageLocation.bucket=ci-failure-agent-backups \
  --set configuration.backupStorageLocation.provider=aws

# Create daily backup schedule
vele ro schedule create daily \
  --schedule="0 2 * * *" \
  --include-namespaces production
```

### Recovery Procedures

```bash
# List available backups
velero backup get

# Restore from backup
velero restore create --from-backup daily-20231214

# Verify restore
kubectl get all -n production
```

---

## Performance Optimization

### Pod Disruption Budget

**k8s/pdb.yaml:**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ci-failure-agent-pdb
  namespace: production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: ci-failure-agent
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ci-failure-agent-network-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: ci-failure-agent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: api
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: database
    ports:
    - protocol: TCP
      port: 5432
```

---

## Cost Optimization

### Spot Instances

```hcl
eks_managed_node_groups = {
  spot = {
    min_size         = 1
    max_size         = 5
    desired_size     = 2
    capacity_type    = "SPOT"
    disk_size        = 20
    instance_types   = ["t3.medium", "t3.large"]
  }
}
```

### Resource Limits and Requests

Always set appropriate resource limits to avoid waste:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "250m"
```

### Monitoring Costs

```bash
# Install Kubecost
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
  --namespace kubecost \
  --create-namespace
```

---

## Success Criteria

- [x] EKS cluster deployed and operational
- [x] Service running with 3+ replicas
- [x] HPA scaling 3-20 pods based on CPU/memory
- [x] Multi-region primary/secondary setup
- [x] Route 53 failover configured
- [x] Velero backups running daily
- [x] Network policies enforced
- [x] Cost < $2000/month

---

**Document Version:** 1.0.0
**Last Updated:** 2025-12-14
**Author:** Infrastructure Team
