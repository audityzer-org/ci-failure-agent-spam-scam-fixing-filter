# Phase 4: Testing and Verification Guide

## Overview

This document provides comprehensive testing and verification procedures for the CI Failure Agent Spam Scam Fixing Filter system. Phase 4 ensures all components integrate correctly and perform under production conditions.

## Table of Contents

1. [Unit Testing](#unit-testing)
2. [Integration Testing](#integration-testing)
3. [Load Testing](#load-testing)
4. [Production Verification](#production-verification)
5. [Monitoring and Alerting](#monitoring-and-alerting)
6. [Rollback Procedures](#rollback-procedures)

---

## Unit Testing

### TaskQueue Unit Tests

Test file: `tests/unit/test_task_queue.py`

**Test Coverage:**
- Task enqueueing with priority levels
- Task dequeuing and FIFO ordering
- Priority queue behavior
- Concurrent task handling
- Error handling and recovery

**Running Tests:**
```bash
pytest tests/unit/test_task_queue.py -v
pytest tests/unit/test_task_queue.py --cov=src.task_queue
```

### State Machine Unit Tests

Test file: `tests/unit/test_state_machine.py`

**Test Coverage:**
- State transitions
- Case lifecycle management
- Invalid state transitions
- Concurrent state updates

**Running Tests:**
```bash
pytest tests/unit/test_state_machine.py -v
```

### WorkflowOrchestrator Unit Tests

Test file: `tests/unit/test_workflow_orchestrator.py`

**Test Coverage:**
- Workflow execution
- DAG validation
- Task dependencies
- Error propagation

**Running All Unit Tests:**
```bash
pytest tests/unit/ -v --cov=src
```

---

## Integration Testing

### Component Integration Tests

Test file: `tests/integration/test_orchestrator_integration.py`

**Test Scenarios:**

#### 1. End-to-End Case Processing
```python
# Submit a case for processing
case_id = "CI-FAILURE-001"
result = orchestrator.process_case(case_id, ci_logs)

# Verify task queue accepted the task
assert task_queue.get_task_count() > 0

# Verify state machine tracked the case
assert state_machine.get_case_status(case_id) == "processing"

# Wait for async processing
await asyncio.sleep(5)

# Verify results
assert result["status"] == "completed"
assert "fixes" in result
```

#### 2. Multiple Concurrent Cases
```bash
pytest tests/integration/test_concurrent_cases.py -v
```

Tests 100 concurrent case submissions to verify:
- Queue capacity handling
- State machine consistency
- No race conditions
- Proper resource cleanup

#### 3. Error Handling and Recovery
```bash
pytest tests/integration/test_error_scenarios.py -v
```

Tests failure scenarios:
- Task timeout handling
- Database connection failures
- Invalid input handling
- Graceful degradation

---

## Load Testing

### Phase 3.3 Load Testing (1000 Concurrent, 10k msg/sec)

Test file: `tests/load/test_load_1000_concurrent.py`

**Test Configuration:**
- 1000 concurrent users
- 10,000 messages/second throughput
- 60-second duration
- Case submission focus

**Running Load Tests:**
```bash
pip install locust
locust -f tests/load/locustfile.py --headless -u 1000 -r 100 --run-time 60s
```

**Expected Metrics:**
- Avg response time: < 500ms
- P99 response time: < 2000ms
- Error rate: < 0.1%
- Throughput: >= 9000 msg/sec

---

## Production Verification

### Pre-Deployment Checklist

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Load test results meet SLOs
- [ ] Code review completed
- [ ] Security scan passed
- [ ] Documentation updated
- [ ] Deployment configuration verified
- [ ] Rollback plan documented
- [ ] Monitoring alerts configured
- [ ] Stakeholders notified

### Deployment Verification

#### 1. Health Check
```bash
curl -X GET https://ci-failure-agent-spam-scam-fixing-filter.onrender.com/health
```

#### 2. Test Case Submission
```bash
curl -X POST https://ci-failure-agent-spam-scam-fixing-filter.onrender.com/api/v1/cases \
  -H "Content-Type: application/json" \
  -d '{"ci_logs": "Build failed"}'
```

---

## Monitoring and Alerting

### Key Metrics to Monitor

- Request latency (p50, p95, p99)
- Error rate and error types
- Task queue depth
- Cases processed per minute
- CPU, memory, disk usage
- Database connection pool utilization

### Alert Thresholds

```yaml
Alerts:
  HighErrorRate:
    condition: error_rate > 1% for 5 minutes
    action: page on-call engineer
    
  HighLatency:
    condition: p99_latency > 5s for 5 minutes
    action: notify slack #alerts
    
  QueueBacklog:
    condition: queue_depth > 10000
    action: notify slack, check capacity
    
  ServiceDown:
    condition: health_check fails 3 times
    action: page on-call engineer, trigger rollback
```

---

## Rollback Procedures

### Automatic Rollback

Trigger automatic rollback if:
- error_rate > 5% for 5 minutes
- p99_latency > 10 seconds for 5 minutes
- service_down: true

### Manual Rollback Steps

1. **Stop Current Deployment**
   ```bash
   render-cli service stop srv-d4uumlre5dus73a3tc0g
   ```

2. **Identify Previous Stable Commit**
   ```bash
   git log --oneline | grep "Commit successful"
   ```

3. **Deploy Previous Version**
   ```bash
   git checkout <stable_commit>
   git push origin HEAD:main
   ```

4. **Verify Health**
   ```bash
   curl -X GET https://ci-failure-agent-spam-scam-fixing-filter.onrender.com/health
   ```

---

## Continuous Testing

### CI/CD Pipeline Testing

All tests run automatically on pull requests:

```yaml
name: Automated Testing
on: [pull_request, push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Unit Tests
        run: pytest tests/unit/ -v
      - name: Integration Tests
        run: pytest tests/integration/ -v
      - name: Code Coverage
        run: pytest --cov=src
```

---

## Success Criteria

Phase 4 is considered complete when:

- [x] 100% unit test pass rate
- [x] 100% integration test pass rate
- [x] Load test achieves > 9000 msg/sec with < 500ms latency
- [x] Service maintains < 0.1% error rate
- [x] All production verification checks pass
- [x] Monitoring alerts configured and tested
- [x] Rollback procedure documented and tested

---

## Next Steps (Phase 5)

1. Kubernetes Cluster Management
2. Auto-scaling policies
3. Multi-region deployment
4. Disaster recovery procedures
5. Performance optimization

---

**Document Version:** 1.0.0
**Last Updated:** 2025-12-14
**Author:** CI/CD Engineering Team
