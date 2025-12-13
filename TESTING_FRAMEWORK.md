# Testing Framework Guide

## Overview

Comprehensive testing framework for the CI Failure Agent system ensuring reliability, performance, and correctness.

## Table of Contents

1. [Unit Testing](#unit-testing)
2. [Integration Testing](#integration-testing)
3. [End-to-End Testing](#end-to-end-testing)
4. [Performance Testing](#performance-testing)
5. [Security Testing](#security-testing)
6. [Test Coverage](#test-coverage)

## Unit Testing

### Framework: pytest

```bash
# Run unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_agent.py::test_parse_failure
```

### Sample Test

```python
import pytest
from src.agent import CIFailureAgent

def test_failure_detection():
    agent = CIFailureAgent()
    log_content = "ERROR: Build failed at step test"
    result = agent.detect_failure(log_content)
    assert result is not None
    assert result.severity == "high"
```

## Integration Testing

### Database Integration

```bash
# Run with test database
PYTEST_DB=test pytest tests/integration/

# Setup test data
pytest tests/integration/ --fixtures
```

### API Testing

```bash
# Test API endpoints
pytest tests/integration/test_api.py -v

# Test with live server
pytest tests/integration/test_api.py --live-server
```

## End-to-End Testing

### Docker Compose Tests

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up

# Run e2e tests
pytest tests/e2e/ -v

# Cleanup
docker-compose -f docker-compose.test.yml down
```

### Kubernetes E2E Tests

```bash
# Deploy test environment
kubectl apply -f k8s/test/

# Run tests
pytest tests/e2e/k8s/ -v

# Cleanup
kubectl delete -f k8s/test/
```

## Performance Testing

### Load Testing with Locust

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

### Sample Load Test

```python
from locust import HttpUser, task, between

class CIFailureAgentUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def analyze_failure(self):
        self.client.post("/analyze", json={"log": "ERROR: test"})
```

### Benchmark Tests

```bash
# Run benchmarks
pytest tests/performance/test_benchmark.py --benchmark-only

# Compare benchmarks
pytest tests/performance/test_benchmark.py --benchmark-only --benchmark-compare=0001
```

## Security Testing

### OWASP Testing

```bash
# Run security scan
bandit -r src/

# Check dependencies
safety check
```

### SQL Injection Tests

```python
def test_sql_injection_prevention():
    agent = CIFailureAgent()
    malicious_input = "'; DROP TABLE logs; --"
    result = agent.query_logs(malicious_input)
    # Verify input is safely escaped
    assert "DROP TABLE" not in result.query
```

### Authentication Tests

```bash
# Test auth endpoints
pytest tests/security/test_auth.py -v

# Test with invalid tokens
pytest tests/security/test_auth.py::test_invalid_token
```

## Test Coverage

### Coverage Requirements

- Minimum 80% overall coverage
- 90% coverage for critical paths
- 100% coverage for security-related code

### Generate Coverage Report

```bash
# HTML report
pytest --cov=src --cov-report=html

# Terminal report
pytest --cov=src --cov-report=term-missing

# Coverage badge
pytest --cov=src --cov-report=term --cov-report=badge
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=src
      - uses: codecov/codecov-action@v2
```

## Test Data Management

### Fixtures

```python
import pytest

@pytest.fixture
def sample_log():
    return "ERROR: Connection timeout"

@pytest.fixture
def mock_database(monkeypatch):
    class MockDB:
        def query(self, sql):
            return []
    monkeypatch.setattr("src.db", MockDB())
```

### Factories

```python
from factory import Factory
from src.models import LogEntry

class LogEntryFactory(Factory):
    class Meta:
        model = LogEntry
    
    timestamp = factory.Faker('date_time')
    message = factory.Faker('text')
    severity = 'error'
```

## Continuous Testing

### Watch Mode

```bash
# Auto-run tests on file changes
pytest-watch tests/
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        types: [python]
        stages: [commit]
```

## Best Practices

1. **Write tests first** (TDD approach)
2. **Keep tests independent** - no test dependencies
3. **Use meaningful names** - describe what is being tested
4. **Mock external dependencies** - reduce flakiness
5. **Test edge cases** - boundary conditions and error paths
6. **Maintain test data** - use factories or fixtures
7. **Review coverage** - identify gaps regularly
8. **Performance tests** - monitor for regressions

## Troubleshooting

### Flaky Tests

```python
# Add retries for unstable tests
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_api_call():
    result = api.get_data()
    assert result is not None
```

### Slow Tests

```bash
# Find slowest tests
pytest --durations=10

# Run only fast tests
pytest -m "not slow"
```

## Documentation

Version: 1.0
Last Updated: 2025-01-01
