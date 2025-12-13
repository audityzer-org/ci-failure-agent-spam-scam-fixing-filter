# CI/CD Verification & Testing Guide

## Overview

Comprehensive CI/CD workflow verification, testing, and validation procedures.

## GitHub Actions Workflow Verification

### 1. Workflow Configuration

```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=src
      - uses: codecov/codecov-action@v3

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v3
      - uses: docker/setup-buildx-action@v2
      - uses: docker/build-push-action@v4
        with:
          push: true
          tags: registry/ci-failure-agent:latest

  deploy:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v3
      - run: |
          kubectl apply -f k8s/
          kubectl rollout status deployment/ci-failure-agent
```

### 2. Workflow Testing

```bash
# Run workflow locally
gh act push --job test
gh act push --job build
gh act push --job deploy

# Verify workflow syntax
gh workflow view .github/workflows/ci.yml
gh workflow list
gh run list --workflow=ci.yml --limit=5
```

## Build Pipeline Verification

### Unit Tests

```bash
pytest tests/unit/ -v --cov=src --cov-report=html
pytest tests/unit/test_agent.py::test_failure_detection -v
```

### Integration Tests

```bash
pytest tests/integration/ -v
pytest tests/integration/test_api.py --live-server
```

### Code Quality

```bash
flake8 src/ --max-line-length=100
black src/ --check
mypy src/ --ignore-missing-imports
safety check
bandit -r src/
```

## Docker Build Verification

```bash
# Build image
docker build -t ci-failure-agent:latest .

# Test image
docker run --rm ci-failure-agent:latest pytest tests/

# Scan for vulnerabilities
trivy image ci-failure-agent:latest
```

## Kubernetes Deployment Verification

### Dry Run

```bash
kubectl apply -f k8s/ --dry-run=client
kubectl diff -f k8s/
```

### Deployment Health

```bash
# Check deployment status
kubectl rollout status deployment/ci-failure-agent
kubectl get deployments -o wide
kubectl get pods -o wide
kubectl describe deployment ci-failure-agent

# Check service endpoints
kubectl get svc
kubectl get endpoints
kubectl describe svc ci-failure-agent
```

### Pod Health

```bash
# Check pod logs
kubectl logs deployment/ci-failure-agent
kubectl logs -f deployment/ci-failure-agent

# Check pod events
kubectl describe pod <pod-name>

# Execute commands in pod
kubectl exec -it <pod> -- /bin/bash
kubectl exec -it <pod> -- curl localhost:8000/health
```

## Smoke Testing

```bash
# Health endpoint
curl http://ci-failure-agent:8000/health

# API endpoint
http POST http://ci-failure-agent:8000/api/analyze \
  log="ERROR: Build failed"

# Database connectivity
kubectl exec -it deployment/ci-failure-agent -- \
  python -c "from app import db; db.test_connection()"

# Redis connectivity
kubectl exec -it deployment/ci-failure-agent -- \
  python -c "import redis; r=redis.Redis(); r.ping()"
```

## Regression Testing

```bash
# Run full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Performance regression
locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 60s
```

## Monitoring & Validation

### Metrics

```bash
# Check application metrics
curl http://ci-failure-agent:8000/metrics

# Query Prometheus
curl http://prometheus:9090/api/v1/query?query=up
```

### Logs

```bash
# Check application logs
kubectl logs deployment/ci-failure-agent

# Check system logs
kubectl logs -l app=ci-failure-agent --all-containers=true
```

## Automated Validation

```bash
#!/bin/bash
set -e

echo "Running CI/CD Verification..."

# Code quality
echo "Testing code quality..."
flake8 src/
black src/ --check
mypy src/

# Unit tests
echo "Running unit tests..."
pytest tests/unit/ --cov=src

# Integration tests
echo "Running integration tests..."
pytest tests/integration/

# Build Docker image
echo "Building Docker image..."
docker build -t ci-failure-agent:latest .

# Deploy to test environment
echo "Deploying to test environment..."
kubectl apply -f k8s/ -n test

# Smoke tests
echo "Running smoke tests..."
pytest tests/smoke/ -v

echo "All CI/CD verifications passed!"
```

## Troubleshooting

### Workflow Failures

```bash
gh run view <run-id> --log
gh run view <run-id> --log-failed
```

### Build Failures

```bash
docker build -t ci-failure-agent:latest . --progress=plain
```

### Deployment Failures

```bash
kubectl rollout history deployment/ci-failure-agent
kubectl rollout undo deployment/ci-failure-agent
```

Version: 1.0
Last Updated: 2025-01-01
