# Production Deployment Guide
## Anti-Corruption Detection & CI/CD Failure Detection System

### Prerequisites
- AWS Account with EKS access
- kubectl CLI configured
- Helm 3+ installed
- Terraform 1.0+
- Docker for local image builds
- GitHub Personal Access Token

### Phase 1: Infrastructure Setup (Terraform)

#### Step 1: Initialize Terraform
```bash
cd terraform/
terraform init \
  -backend-config="bucket=audityzer-terraform-state" \
  -backend-config="key=prod/eks/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true" \
  -backend-config="dynamodb_table=terraform-locks"
```

#### Step 2: Plan Infrastructure
```bash
terraform plan \
  -var="cluster_name=audityzer-prod" \
  -var="aws_region=us-east-1" \
  -var="vpc_cidr=10.0.0.0/16" \
  -var="instance_type=t3.medium" \
  -var="desired_size=3" \
  -var="min_size=3" \
  -var="max_size=10" \
  -out=tfplan
```

#### Step 3: Apply Infrastructure
```bash
terraform apply tfplan
terraform output > cluster_info.json
```

#### Step 4: Configure kubectl
```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name audityzer-prod

kubectl cluster-info
kubectl get nodes
```

### Phase 2: Cluster Preparation

#### Step 1: Create Namespaces
```bash
kubectl create namespace production
kubectl create namespace staging
kubectl create namespace monitoring
kubectl create namespace argocd
```

#### Step 2: Setup RBAC
```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: anti-corruption
  namespace: production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: anti-corruption
  namespace: production
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
EOF
```

#### Step 3: Create Secrets
```bash
kubectl create secret generic anti-corruption-db-secret \
  --from-literal=url="postgresql://user:pass@host:5432/db" \
  -n production

kubectl create secret generic anti-corruption-redis-secret \
  --from-literal=url="redis://host:6379" \
  -n production

kubectl create secret generic anti-corruption-api-secret \
  --from-literal=key="your-api-key-here" \
  -n production
```

### Phase 3: Monitoring Stack

#### Step 1: Install Prometheus
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/prometheus \
  --namespace monitoring \
  --values monitoring/prometheus-values.yaml
```

#### Step 2: Install Grafana
```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install grafana grafana/grafana \
  --namespace monitoring \
  --set adminPassword=admin \
  --set persistence.enabled=true
```

#### Step 3: Deploy Monitoring Rules
```bash
kubectl apply -f monitoring/prometheus-rules.yaml
```

### Phase 4: GitOps Setup (ArgoCD)

#### Step 1: Install ArgoCD
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

#### Step 2: Access ArgoCD UI
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Access at https://localhost:8080

# Get initial password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

#### Step 3: Deploy Application via ArgoCD
```bash
kubectl apply -f gitops/argocd-application.yaml
```

### Phase 5: Service Deployment

#### Step 1: Create Deployment via Helm
```bash
helm repo add audityzer https://charts.audityzer.com
helm repo update

helm install anti-corruption audityzer/anti-corruption \
  --namespace production \
  --values helm/values-production.yaml \
  --set image.tag="latest"
```

#### Step 2: Verify Deployment
```bash
kubectl rollout status deployment/anti-corruption-orchestrator -n production
kubectl get pods -n production
kubectl logs -f deployment/anti-corruption-orchestrator -n production
```

#### Step 3: Expose via Ingress
```bash
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: anti-corruption-ingress
  namespace: production
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.audityzer.com
    secretName: audityzer-tls
  rules:
  - host: api.audityzer.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: anti-corruption
            port:
              number: 80
EOF
```

### Phase 6: Verification & Testing

#### Health Checks
```bash
# Service health
curl https://api.audityzer.com/health/ready

# Metrics
kubectl port-forward svc/anti-corruption 8090:8090 -n production
curl http://localhost:8090/metrics

# Pod status
kubectl describe pod -l app=anti-corruption -n production
```

#### Load Testing
```bash
kubectl run load-test \
  --image=grafana/k6:latest \
  --rm -it \
  --restart=Never \
  --env="URL=https://api.audityzer.com" \
  -- run -
```

### Phase 7: Monitoring & Maintenance

#### Dashboards
- Grafana: http://localhost:3000 (grafana service)
- Prometheus: http://localhost:9090 (prometheus service)
- ArgoCD: https://localhost:8080 (argocd-server)

#### Scaling
```bash
# Manual scaling
kubectl scale deployment anti-corruption-orchestrator \
  --replicas=5 -n production

# Auto-scaling already configured in deployment manifest
# Min 3, Max 10 replicas based on CPU/Memory
```

#### Backup & Recovery
```bash
# Backup etcd
kubectl get all -n production -o yaml > production-backup.yaml

# Restore
kubectl apply -f production-backup.yaml
```

### Troubleshooting

#### Pod not starting
```bash
kubectl describe pod <pod-name> -n production
kubectl logs <pod-name> -n production --previous
```

#### High latency
```bash
# Check HPA status
kubectl get hpa -n production

# Check resource usage
kubectl top nodes
kubectl top pod -n production
```

#### Deployment failures
```bash
# Check ArgoCD sync status
argocd app get anti-corruption

# Check helm values
helm get values anti-corruption -n production
```

### Rollback Procedure

```bash
# If deployment fails
helm rollback anti-corruption 0 -n production

# Check history
helm history anti-corruption -n production

# Via kubectl
kubectl rollout undo deployment/anti-corruption-orchestrator -n production
```

### Success Criteria
- ✅ All pods running and ready
- ✅ Health endpoints responding
- ✅ Metrics flowing to Prometheus
- ✅ ArgoCD showing app as Synced
- ✅ API endpoints responding < 100ms
- ✅ Error rate < 1%

---
**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Support**: infrastructure@audityzer.com
