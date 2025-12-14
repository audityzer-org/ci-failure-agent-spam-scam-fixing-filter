# Phase 3: Predictive Propositions - Implementation Guide

## Integration Timeline in NEXT_STEPS.md Context

Predictive Propositions Service must align with production deployment phases:
- **Phase 1-2 (Weeks 1-2):** Infrastructure ready
- **Phase 3-4 (Weeks 2-4):** Integrate propositions API
- **Phase 5+ (Weeks 4+):** ML model deployment

---

## 1. CI Failure Fix Ranker (Phase 3, Week 2)

### Implementation: services/predictive-suggestions/ci_failure_proposer.py

```python
# Error pattern matching
FAILURE_TEMPLATES = {
    'timeout': {
        'pattern': r'timeout|timed out|deadline',
        'propositions': [
            {'title': 'Increase timeout', 'action': 'increase_timeout', 'increase_by': '300s'},
            {'title': 'Check resource limits', 'action': 'check_resources'}
        ]
    },
    'oom': {
        'pattern': r'OutOfMemory|OOM|Memory exceeded',
        'propositions': [
            {'title': 'Increase memory', 'action': 'increase_memory', 'increase_by': '512Mi'},
            {'title': 'Enable swap', 'action': 'enable_swap'}
        ]
    }
}
```

### Endpoint: POST /services/predict/suggest
Input: error_logs + failure_type
Output: Top 5 CI fixes with confidence scores

---

## 2. Spam/Scam Triage Ranker (Phase 3, Week 2)

### Implementation: services/predictive-suggestions/spam_scam_proposer.py

Logic:
- Confidence >= 0.9: **Auto-block + notify security team**
- Confidence 0.7-0.9: **Queue for human review**  
- Confidence < 0.7: **Log and monitor**

Signals:
- IP geolocation mismatch
- Email domain reputation
- Suspicious repository behavior
- Unusual API patterns

---

## 3. Logging Pipeline (Phase 3, Week 3)

### PostgreSQL Schema
```sql
CREATE TABLE proposition_logs (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(255),
    proposition_id VARCHAR(255),
    user_action VARCHAR(50),  -- accepted/rejected/skipped
    confidence FLOAT,
    timestamp TIMESTAMPTZ,
    actual_resolution TEXT
);

CREATE INDEX idx_incident ON proposition_logs(incident_id);
CREATE INDEX idx_timestamp ON proposition_logs(timestamp);
```

### Redis Caching
- Cache top 10 propositions per failure type
- TTL: 1 hour
- Flush on new ML model deployment

---

## 4. Kubernetes Deployment (Phase 4, Week 3)

### Helm Values (values-production.yaml)
```yaml
predicrive-suggestions:
  replicaCount: 3
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
  
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
  
  postgresql:
    enabled: true
    auth:
      password: ${DB_PASSWORD}
  
  redis:
    enabled: true
    auth:
      enabled: true
```

---

## 5. Monitoring & Alerting (Phase 3, Week 3)

### Prometheus Metrics
- `proposition_latency_ms` - P99 < 200ms
- `proposition_acceptance_rate` - Target > 60%
- `ci_fix_success_rate` - Track outcomes
- `spam_precision` - Target > 85%

### Grafana Dashboard
Show:
- Proposition acceptance trends
- CI fix success rates by category
- Spam detection accuracy
- API latency percentiles

---

## 6. Integration with anti-corruption-orchestrator

### Call Point: Before escalation decision
```python
# In orchestrator.py
propositions = await predict_client.suggest(
    incident_id=incident.id,
    incident_type='ci_failure',
    failure_type=incident.failure_type,
    error_logs=incident.error_logs
)

# Present top 3 propositions to user
# Log selected proposition for feedback
```

---

## 7. Load Testing (Phase 5, Week 5)

### k6 Test Script
```javascript
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 100,
  duration: '5m',
};

export default function () {
  const res = http.post('/services/predict/suggest', {
    incident_type: 'ci_failure',
    error_logs: ['timeout error log']
  });
  check(res, { 'status 200': (r) => r.status === 200 });
}
```

Target: p99 latency < 200ms under 100 concurrent requests

---

## 8. Success Criteria

✅ User acceptance rate > 60%
✅ API latency p99 < 200ms  
✅ CI fix success tracking enabled
✅ Spam precision > 85%
✅ 1000+ feedback events logged in 4 weeks
✅ Integrated with anti-corruption-orchestrator
✅ Production monitoring active
