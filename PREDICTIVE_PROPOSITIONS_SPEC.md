# Predictive Propositions Feature Specification

## 1. Feature Definition & Requirements

### 1.1 Overview
A **Predictive Propositions System** that provides intelligent, context-aware suggestions to users dealing with CI failures and security incidents (spam/scam). The system operates as a **fallback recommendation engine** when the main predictive-propositions-service is unavailable, and can complement it when online.

### 1.2 Goals
- **Primary**: Reduce time-to-action (TTIA) for incident resolution by 20-30%
- **Secondary**: Improve user confidence in system recommendations (↑ CTR by 15%)
- **Tertiary**: Collect training data for ML ranking model refinement

### 1.3 User Contexts
1. **Alert Dashboard**: DevOps engineers viewing failed CI pipelines
2. **Security Console**: Security teams reviewing spam/scam incidents
3. **API Consumers**: Teams integrating with orchestration_engine

### 1.4 Proposition Types & Placement

| Context | Proposition Type | Placement | Max Count | Format |
|---------|------------------|-----------|-----------|--------|
| CI Failure | Test/Build fix steps | Inline in alert | 1-2 | Rich card |
| Security | Action (ignore/report/verify) | Modal popup | 1-3 | Ranked list |
| API | Structured metadata | JSON response | 5 | Rank score |

### 1.5 Success Metrics

#### Primary Metrics
- **Click-Through Rate (CTR)**: Baseline 5% → Target 20% (Tier 1)
- **Time-to-Action (TTIA)**: Baseline 5min → Target 2min (Tier 2)
- **Adoption Rate**: % of users accepting ≥1 proposition/month (Target: 60%)

#### Secondary Metrics
- **Proposal Quality Score**: (accepted / shown) (Target: ≥15%)
- **ML Model Accuracy**: Ranking model precision@3 (Target: ≥70%)
- **User Satisfaction**: Post-action survey score (Target: ≥4.0/5)

#### Technical Metrics
- **Latency**: p95 < 100ms for proposition fetch (cache hit < 10ms)
- **Cache Hit Ratio**: ≥85% for repeated alerts
- **Backend Load**: <5% increase in orchestration_engine CPU

### 1.6 Constraints & Non-Functional Requirements

**Latency**:
- API response: < 100ms (p95)
- Dashboard render: < 500ms (including fetch)

**Privacy & Security**:
- Never log user PII (only alert_id, alert_type)
- Scrub sensitive env vars from suggestions
- All logs encrypted at rest

**Data Retention**:
- Proposition click logs: 90 days
- ML training data: 1 year
- User feedback: 180 days

**Availability**:
- Fallback engine: 99.5% uptime (resilient to main service outage)
- Graceful degradation when ML model unavailable

---

## 2. System Architecture

### 2.1 High-Level Design

```
User Alert → orchestration_engine → SuggestionEngine → Cache (Redis)
                                   → RuleRepository (local)
                                   → MLRanker (optional, fallback to rules)
                                   → User Decision → Log (Prometheus/CloudWatch)
```

### 2.2 Data Signals

#### Signal Sources
1. **Current Alert**: alert_type, alert_description, severity
2. **User History**: recent_incident_types (last 7 days), avg_resolution_time
3. **Global Trends**: top_incident_types (last 24h), seasonal patterns
4. **Context**: deployment_frequency, incident_rate_percentile

#### Signal Combination
```python
feature_vector = {
    'alert_type_embedding': embed(alert.type),  # one-hot or learned
    'recency_score': exp(-time_since_similar_incident / decay),
    'user_expertise_level': user_resolution_time / avg_resolution_time,
    'global_trend_weight': incident_type_frequency_ratio,
    'time_of_day': hour (cyclical encoding),
}
```

### 2.3 Computation Location

| Phase | Location | Rationale |
|-------|----------|----------|
| **Candidate Generation** | Backend (SuggestionEngine) | Needs user history + trends |
| **Rule Matching** | On-device or Backend | Fast local rules for CI failures |
| **ML Ranking** | Backend (cached model) | Complex features, model inference |
| **Caching** | Redis + Local Cache | Multi-tier: API response caching |

### 2.4 Caching Strategy

**Three-Tier Cache**:
1. **Local In-Memory Cache**: (app level)  
   - TTL: 5 minutes  
   - Keys: `alert_type:suggestion_type`  
   - Hit ratio: ~70% (same alerts repeat often)

2. **Redis Cache** (shared):  
   - TTL: 30 minutes  
   - Keys: `proposition:alert_id`  
   - Hit ratio: ~15% (personalized histories)

3. **Computed On-Demand**:  
   - TTL: inline (sub-100ms compute)
   - For new alert combinations

**Cache Invalidation**:
- On user decision accepted → invalidate personalized cache
- On new trend detected (hourly) → invalidate global cache
- On rule update → flush local rule cache

---

## 3. ML Approach

### 3.1 Baseline (Phase 1)
**Rule-Based + Frequency Heuristics**
```python
# Implemented in src/predictive_suggestions/rules.py
rule_confidence = {  
    'test_failure': 0.95,  # AssertionError, etc.
    'build_error': 0.98,   # SyntaxError, ImportError
    'timeout': 0.92,
    'phishing': 0.85,
}

# Heuristic ranking:
rank_score = rule_confidence * frequency_weight * recency_boost
```

**Evaluation**: A/A test (no ML) vs. baseline rules

### 3.2 Intermediate (Phase 2 — MVP+3 months)
**Ranking Model** (Logistic Regression / LightGBM)

**Features**:  
- Alert type (categorical)  
- User expertise (continuous: resolution_time_ratio)  
- Incident recency (continuous: days_since_similar)  
- Global frequency (continuous: percentile)  
- Time-of-day (cyclical: sin/cos encoding)  
- Severity level (ordinal)  

**Target**: P(user accepts proposition)

**Training**:
- Data: 30-day proposition click logs
- Sampling: Stratified by alert_type
- Validation: Hold-out 20% (temporal split: last 1 week)

**Deployment**:
- Cold-start: fallback to rules
- Warm-start: cached model predictions
- Monitoring: precision@3, recall@3

### 3.3 Advanced (Phase 3 — MVP+6 months)
**Hybrid: LLM Candidate Generation + ML Ranking**

```python
# Pseudo-code
candidates_llm = llm_generator.generate(
    alert_text,
    top_k=10,  # Generate 10 candidate propositions
    context={
        'user_history': [...],
        'similar_incidents': [...],
    }
)

# Rank with lightweight model
ranked = ml_ranker.rank(candidates_llm, feature_vector)
propositions = ranked[:3]  # Return top 3
```

**Why**:
- LLM can generate novel suggestions (not rule-limited)
- ML ranker maintains latency & controls quality
- Fewer hallucinations via re-ranking

---

## 4. A/B Testing & Experimentation

### 4.1 Test Design

**Experiment**: "Rules-Based Propositions (MVP)"  
**Duration**: 3 weeks  
**Hypothesis**: Users shown propositions will resolve incidents 25% faster.  

**Traffic Split**:
- **Control**: No propositions (baseline)
- **Treatment**: Rules-based propositions (new)
- **Size**: 50% / 50% (random by user_id)

**Guardrails** (abort if any trigger):
- CTR < 2% for 2 consecutive days
- TTIA > +50% (worse resolution times)
- User complaint rate > 10% increase

### 4.2 Metrics

**Primary Metrics** (MDE = Minimum Detectable Effect):
1. **Time-to-Action (TTIA)**: MDE = -20% (should reduce by 1 minute)
2. **Acceptance Rate**: MDE = +5% (baseline ~5%)

**Secondary Metrics**:
- CTR (baseline 5% → target 20%)
- User satisfaction (post-action survey)
- Proposition accuracy (manual labeling sample)

**Statistical Test**:
- Two-sided t-test (α=0.05, β=0.2)
- Sample size: ~5,000 alerts per arm for TTIA significance
- Duration: 3 weeks (capture Mon-Fri + weekend patterns)

### 4.3 Instrumentation

```python
# Logging (Python)
logger.info("proposition_shown", {
    "alert_id": "...",
    "alert_type": "CI_FAILURE",
    "proposition_id": "...",
    "rank_position": 1,
    "timestamp": "...",
})

logger.info("proposition_clicked", {
    "alert_id": "...",
    "proposition_id": "...",
    "action_taken": "apply_fix",  # or "ignore", "report"
    "resolution_time_seconds": 120,
    "timestamp": "...",
})
```

### 4.4 Go/No-Go Criteria

| Metric | Control | Treatment | Decision |
|--------|---------|-----------|----------|
| TTIA | 5.0 min | 4.0 min (MDE) | GO ✓ |
| Acceptance Rate | 5% | 10% (MDE) | GO ✓ |
| CTR | 5% | 20% (aspirational) | NICE-TO-HAVE |
| Satisfaction | 3.8/5 | 4.2/5+ | GO ✓ |

**Rollout**:
- Week 1: 10% → observe guardrails
- Week 2: 50% → measure metrics
- Week 3: 100% (if GO)

---

## 5. Implementation Roadmap

### Phase 1 (MVP — Current)
- [x] Rule-Based Engine (src/predictive_suggestions/)
- [x] Fallback Integration into orchestration_engine.py
- [x] Unit & E2E Tests
- [ ] Basic Logging (PropositionLog → CloudWatch)
- [ ] A/B Test Harness

### Phase 2 (MVP + 3 months)
- [ ] Collect 30-day proposition logs
- [ ] Build ML ranking model (LightGBM)
- [ ] Deploy model via MLflow / TensorFlow Lite
- [ ] Upgrade to ML-based ranking
- [ ] Monitor model drift

### Phase 3 (MVP + 6 months)
- [ ] Evaluate LLM candidate generation
- [ ] Integrate (optional) LLM API
- [ ] Hybrid ranking pipeline
- [ ] Advanced metrics dashboard

---

## 6. Open Questions & Decisions

1. **LLM Integration**: Use Claude/GPT for candidate generation or stick with rules?
   - Recommendation: Start rules-only (MVP), add LLM in Phase 3

2. **Per-User vs. Per-Alert Personalization**?
   - Current: Per-alert type (fast, stateless)
   - Future: Per-user history (slower, requires session state)

3. **Fallback Graceful Degradation**:
   - If ML model fails: fall back to rules?
   - If cache fails: compute on-demand or return empty?
   - Recommendation: rules → rules, cache → on-demand

4. **User Feedback Mechanism**:
   - Thumbs up/down on propositions?
   - Explicit "does this help?" survey?
   - Recommendation: Implicit (accept = thumb up, ignore = thumb down)

---

## Appendix: Data Schema

### PropositionLog Table
```sql
CREATE TABLE proposition_logs (
    id UUID PRIMARY KEY,
    alert_id UUID,
    alert_type VARCHAR(50),
    proposition_id VARCHAR(100),
    proposition_rank INT,
    user_id UUID,
    action_taken VARCHAR(50),  -- 'accepted', 'ignored', 'reported'
    resolution_time_seconds INT,
    model_source VARCHAR(50),  -- 'rules', 'ml', 'llm'
    confidence_score FLOAT,
    created_at TIMESTAMP,
    INDEX (alert_id, created_at),
    INDEX (user_id, created_at)
);
```

### Feature Vector
```json
{
  "alert_type": "test_failure",
  "severity": "high",
  "user_expertise_ratio": 1.2,
  "days_since_similar": 3.5,
  "global_frequency_percentile": 75,
  "hour_of_day": 14,
  "is_weekend": false
}
```
