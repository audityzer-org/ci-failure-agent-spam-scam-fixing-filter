# Staging Deployment Guide - Phase 3.2

## Quick Start for Integration Testing

### Prerequisites
- Docker installed
- Docker Compose
- Python 3.11+
- Git

### Step 1: Clone and Setup

```bash
git clone https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter.git
cd ci-failure-agent-spam-scam-fixing-filter
```

### Step 2: Build Docker Image

```bash
docker build -t ci-failure-agent:staging .
```

### Step 3: Start Services Locally

#### Option A: Docker Compose (Recommended)

Create `docker-compose.staging.yml`:

```yaml
version: '3.8'
services:
  orchestration-engine:
    image: ci-failure-agent:staging
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=INFO
    volumes:
      - ./src:/app/src
    command: python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

  predictive-service:
    image: predictive-propositions:staging
    ports:
      - "8001:8001"
    environment:
      - PYTHONUNBUFFERED=1
    command: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8001

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=ci_failure_staging
      - POSTGRES_USER=staging
      - POSTGRES_PASSWORD=staging
```

Start services:

```bash
docker-compose -f docker-compose.staging.yml up
```

#### Option B: Local Python

```bash
# Install dependencies
pip install -r requirements.txt

# Start orchestration engine
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# In another terminal, start predictive service
python -m uvicorn src/predictive_actions_api:app --host 0.0.0.0 --port 8001
```

### Step 4: Run Integration Tests

```bash
# Run all integration tests
pytest tests/test_integration_platform.py -v -s

# Run specific test
pytest tests/test_integration_platform.py::TestPlatformIntegration::test_alert_to_ui_flow -v

# Run with coverage
pytest tests/test_integration_platform.py --cov=src --cov-report=html
```

### Step 5: Test API Endpoints

#### Health Check

```bash
curl http://localhost:8000/health
```

#### Send Alert

```bash
curl -X POST http://localhost:8000/api/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-alert-1",
    "type": "ci_failure",
    "description": "Build failed: unit tests",
    "severity": "high",
    "timestamp": "2025-12-16T20:00:00Z",
    "source": "jenkins",
    "metadata": {"build_id": "123"}
  }'
```

#### Get Predictive Actions

```bash
curl -X POST http://localhost:8001/api/predictive_actions \
  -H "Content-Type: application/json" \
  -d '{
    "alert_type": "ci_failure",
    "description": "Build failed",
    "severity": "high",
    "metadata": {"build_id": "123"}
  }'
```

### Step 6: Monitor Logs

```bash
# Docker
docker-compose -f docker-compose.staging.yml logs -f orchestration-engine

# Local
pytest tests/test_integration_platform.py -v -s --log-cli-level=DEBUG
```

## Testing Checklist

- [ ] Health check endpoint responds (200 OK)
- [ ] Alert endpoint accepts alerts
- [ ] Predictive service returns action recommendations
- [ ] UI components render correctly
- [ ] JSON serialization works
- [ ] Concurrent alerts processed correctly
- [ ] Error handling for service failures
- [ ] Performance baseline < 500ms response time

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Service Connection Issues

```bash
# Check if services are running
docker ps

# Check service logs
docker logs <container-name>

# Restart services
docker-compose -f docker-compose.staging.yml restart
```

### Database Connection Issues

```bash
# Check PostgreSQL
psql -h localhost -U staging -d ci_failure_staging

# Reset database
docker-compose -f docker-compose.staging.yml down -v
docker-compose -f docker-compose.staging.yml up
```

## Next Steps

1. **Integration Testing**: Run all test suites
2. **Performance Testing**: Load test with concurrent alerts
3. **UAT**: User acceptance testing with staging platform
4. **Production Deployment**: Follow NEXT_STEPS.md Phase 1

## Documentation

- [NEXT_STEPS.md](./NEXT_STEPS.md) - Production roadmap
- [PREDICTIVE_ACTIONS_INTEGRATION_GUIDE.md](./PREDICTIVE_ACTIONS_INTEGRATION_GUIDE.md) - API documentation
- [tests/test_integration_platform.py](./tests/test_integration_platform.py) - Integration tests

## Support

For issues or questions:
1. Check logs first
2. Review test output
3. Open GitHub issue with logs and steps to reproduce
