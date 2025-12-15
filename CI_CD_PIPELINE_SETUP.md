# CI/CD Pipeline Setup Guide
## GitHub Actions + Docker + Kubernetes Deployment
### For auditorsec.com & audityzer.com Infrastructure

---

## Overview

This guide provides a complete CI/CD pipeline using GitHub Actions to automatically:
1. Build Docker images
2. Run tests
3. Push to container registry (ECR)
4. Deploy to Kubernetes cluster (EKS)
5. Update infrastructure on auditorsec.com and audityzer.com

## Prerequisites

### AWS Account Setup
```bash
# Create ECR Repository
aws ecr create-repository --repository-name ci-failure-agent --region us-east-1

# Create IAM User for GitHub Actions
aws iam create-user --user-name github-actions-ci

# Attach ECR permissions
aws iam attach-user-policy --user-name github-actions-ci \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

# Create access keys
aws iam create-access-key --user-name github-actions-ci
```

### GitHub Repository Secrets

Add these secrets to your GitHub repository (Settings > Secrets):

```yaml
AWS_ACCESS_KEY_ID: <from IAM user>
AWS_SECRET_ACCESS_KEY: <from IAM user>
AWS_REGION: us-east-1
AWS_ACCOUNT_ID: <your AWS account ID>
ECR_REGISTRY: <account_id>.dkr.ecr.us-east-1.amazonaws.com
ECR_REPOSITORY: ci-failure-agent
EKS_CLUSTER_NAME: ci-failure-agent-cluster
KUBERNETES_NAMESPACE: ci-failure-agent
DOCKER_USERNAME: <Docker Hub username>
DOCKER_PASSWORD: <Docker Hub token>
```

## GitHub Actions Workflow

### Main Build Pipeline (.github/workflows/main.yml)

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: ${{ secrets.ECR_REGISTRY }}
  ECR_REPOSITORY: ${{ secrets.ECR_REPOSITORY }}
  IMAGE_TAG: ${{ github.sha }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov black flake8
      
      - name: Run linting
        run: |
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
          black --check .
      
      - name: Run tests
        run: pytest --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build Docker image
        run: |
          docker build -t ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:${{ env.IMAGE_TAG }} .
          docker tag ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:${{ env.IMAGE_TAG }} \
                     ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:latest
      
      - name: Push to Amazon ECR
        run: |
          docker push ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:${{ env.IMAGE_TAG }}
          docker push ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:latest

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig --name ${{ secrets.EKS_CLUSTER_NAME }} --region ${{ env.AWS_REGION }}
      
      - name: Update deployment image
        run: |
          kubectl set image deployment/ci-failure-agent \
            ci-failure-agent=${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:${{ env.IMAGE_TAG }} \
            -n ${{ secrets.KUBERNETES_NAMESPACE }}
      
      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/ci-failure-agent \
            -n ${{ secrets.KUBERNETES_NAMESPACE }} --timeout=5m
      
      - name: Verify deployment
        run: |
          kubectl get pods -n ${{ secrets.KUBERNETES_NAMESPACE }}
          kubectl get svc -n ${{ secrets.KUBERNETES_NAMESPACE }}
```

## Deployment Stages

### Stage 1: Testing
- Run unit tests
- Code quality checks (flake8, black)
- Security scanning
- Coverage reports

### Stage 2: Build
- Build Docker image
- Scan for vulnerabilities
- Tag with git SHA and latest

### Stage 3: Push
- Push to ECR
- Update image manifest

### Stage 4: Deploy
- Update EKS deployment
- Health checks
- Rollback on failure

## Manual Deployment

### Using kubectl
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/ci-failure-agent-deployment.yaml
kubectl apply -f k8s/ci-failure-agent-ingress.yaml

# Check status
kubectl get pods -n ci-failure-agent
kubectl describe pod <pod-name> -n ci-failure-agent
kubectl logs <pod-name> -n ci-failure-agent
```

### Using Helm
```bash
helm repo add ci-failure-agent https://charts.example.com
helm install ci-failure-agent ci-failure-agent/ci-failure-agent \
  -n ci-failure-agent \
  --values values.yaml
```

## Monitoring and Logging

### CloudWatch Logs
```bash
aws logs tail /aws/eks/ci-failure-agent-cluster --follow
```

### Prometheus Metrics
```bash
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Access: http://localhost:9090
```

### Grafana Dashboards
```bash
kubectl port-forward -n monitoring svc/grafana 3000:80
# Access: http://localhost:3000
```

## Rollback Procedure

```bash
# Check previous deployments
kubectl rollout history deployment/ci-failure-agent -n ci-failure-agent

# Rollback to previous version
kubectl rollout undo deployment/ci-failure-agent -n ci-failure-agent

# Rollback to specific revision
kubectl rollout undo deployment/ci-failure-agent --to-revision=2 -n ci-failure-agent
```

## Troubleshooting

### Pod not starting
```bash
kubectl describe pod <pod-name> -n ci-failure-agent
kubectl logs <pod-name> -n ci-failure-agent
```

### Image pull errors
```bash
# Verify ECR access
aws ecr describe-repositories --region us-east-1

# Check image exists
aws ecr describe-images --repository-name ci-failure-agent --region us-east-1
```

### Network issues
```bash
# Check service endpoints
kubectl get endpoints -n ci-failure-agent

# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup ci-failure-agent.ci-failure-agent.svc.cluster.local
```

## Best Practices

1. **Semantic Versioning**: Use git tags for releases
2. **Immutable Images**: Use git SHA for image tags
3. **Health Checks**: Implement liveness and readiness probes
4. **Resource Limits**: Define CPU and memory requests/limits
5. **Security**: Use private repositories and RBAC
6. **Monitoring**: Collect metrics and logs
7. **Documentation**: Keep runbooks updated

## Security Considerations

- Use IAM roles for authentication
- Encrypt secrets at rest and in transit
- Scan images for vulnerabilities
- Use network policies
- Enable audit logging
- Regular backup of database

## Support and Documentation

- AWS EKS Documentation: https://docs.aws.amazon.com/eks/
- GitHub Actions: https://docs.github.com/en/actions
- Kubernetes: https://kubernetes.io/docs/
- Docker: https://docs.docker.com/

---

**Last Updated**: 2024
**Version**: 1.0.0
**Maintained By**: DevOps Team
