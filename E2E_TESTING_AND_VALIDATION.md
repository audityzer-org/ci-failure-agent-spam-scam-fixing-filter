# End-to-End Testing & Validation Guide
## Complete Pipeline Testing for auditorsec.com & audityzer.com

---

## 1. Test Strategy Overview

### Test Levels:
1. **Unit Tests** - Individual function testing (pytest)
2. **Integration Tests** - Component interaction testing
3. **API Tests** - REST endpoint testing
4. **E2E Tests** - Full workflow testing
5. **Performance Tests** - Load and stress testing
6. **Security Tests** - SAST/DAST scanning

### Testing Tools:
- `pytest` - Unit testing framework
- `pytest-cov` - Coverage reporting
- `locust` - Load testing
- `Selenium` - UI automation (optional)
- `OWASP ZAP` - Security scanning
- `sonarqube` - Code quality

## 2. Unit Testing

### Running Tests
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run with markers
pytest tests/ -m "unit"
```

### Test Structure
```
tests/
├── unit/
│   ├── test_models.py
│   ├── test_validators.py
│   └── test_utils.py
├── integration/
│   ├── test_database.py
│   └── test_external_apis.py
├── e2e/
│   ├── test_deployment.py
│   └── test_full_workflow.py
└── conftest.py
```

## 3. Integration Testing

### Database Integration
```python
@pytest.fixture
def test_db():
    db = create_test_database()
    yield db
    db.cleanup()

def test_user_creation(test_db):
    user = test_db.create_user("test@example.com")
    assert user.id is not None
```

### API Integration
```python
def test_api_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

## 4. End-to-End Testing

### Kubernetes Deployment Test
```bash
#!/bin/bash

# Deploy to test cluster
kubectl apply -f k8s/ci-failure-agent-deployment.yaml

# Wait for deployment
kubectl rollout status deployment/ci-failure-agent -n ci-failure-agent

# Get service endpoint
SERVICE_IP=$(kubectl get svc ci-failure-agent -n ci-failure-agent -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test health endpoint
curl -f http://$SERVICE_IP/health

# Test API endpoints
curl -f http://$SERVICE_IP/api/v1/status

# Verify metrics
curl -f http://$SERVICE_IP/metrics
```

### Domain Testing
```bash
# Test auditorsec.com
curl -f https://auditorsec.com/health

# Test audityzer.com
curl -f https://audityzer.com/health

# Check SSL certificate
openssl s_client -connect auditorsec.com:443
```

## 5. Load Testing

### Locust Script
```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 5)
    
    @task
    def health_check(self):
        self.client.get("/health")
    
    @task(3)
    def get_status(self):
        self.client.get("/api/v1/status")
    
    @task(2)
    def create_audit(self):
        self.client.post("/api/v1/audits", json={"name": "Test"})
```

### Running Load Tests
```bash
# Start Locust
locust -f tests/load/locustfile.py --host=https://auditorsec.com

# Headless mode
locust -f tests/load/locustfile.py --host=https://auditorsec.com \
  --users 100 --spawn-rate 10 --run-time 5m
```

## 6. Performance Validation

### Metrics to Monitor
- Response time < 200ms (p95)
- Error rate < 0.1%
- Throughput > 1000 req/s
- Memory usage < 1GB
- CPU usage < 50%

### Prometheus Queries
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time
histogram_quantile(0.95, http_request_duration_seconds)

# Pod memory
sum(container_memory_usage_bytes{pod=~"ci-failure-agent.*"})
```

## 7. Security Testing

### SAST (Static Analysis)
```bash
# Bandit - Python security
bandit -r . -f json -o bandit-report.json

# SonarQube scanning
sonar-scanner \
  -Dsonar.projectKey=ci-failure-agent \
  -Dsonar.sources=src
```

### DAST (Dynamic Analysis)
```bash
# OWASP ZAP
zap-cli scan -r report.html https://auditorsec.com
```

### Dependency Scanning
```bash
# Check for vulnerabilities
pip-audit
safety check
```

## 8. Validation Checklist

### Pre-Deployment
- [ ] All tests passing (>80% coverage)
- [ ] Code review completed
- [ ] Security scan passed
- [ ] Performance benchmarks met
- [ ] Documentation updated

### Post-Deployment
- [ ] Application responding to health checks
- [ ] Load balancer routing traffic
- [ ] SSL certificates valid
- [ ] Logs flowing to CloudWatch
- [ ] Metrics available in Prometheus
- [ ] Alerts configured

## 9. Rollback Procedure

```bash
# Check deployment history
kubectl rollout history deployment/ci-failure-agent

# Rollback to previous version
kubectl rollout undo deployment/ci-failure-agent

# Rollback to specific revision
kubectl rollout undo deployment/ci-failure-agent --to-revision=5

# Monitor rollback progress
kubectl rollout status deployment/ci-failure-agent
```

## 10. CI/CD Pipeline Integration

All tests run automatically via GitHub Actions before deployment.

---

**Last Updated**: 2024
**Version**: 1.0.0
