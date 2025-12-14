# Phase 3: Predictive Propositions & ML Ranker

## Quick Summary

Predictive Propositions Service provides intelligent recommendations in two contexts:
1. **CI Failure Fixes** - Automated suggestions for common build/deploy errors
2. **Spam/Scam Triage** - Recommended actions for suspicious incidents

## Strategy Decision: Dual Role

Rather than building separate services, integrate one propositions service that handles both contexts based on `incident_type` parameter.

## Phase 3 Implementation Tasks

### Task 1: Rule-Based Ranker (CI Failures)
- Parse error logs with regex patterns
- Match against failure templates
- Rank by historical success rate
- Examples: timeout, OOM, network errors

### Task 2: Rule-Based Ranker (Spam/Scam)
- Confidence > 0.9 -> Auto-block + notify
- Confidence 0.7-0.9 -> Queue for review
- Confidence < 0.7 -> Log and monitor

### Task 3: Logging Pipeline
- Track all propositions shown
- Log user actions (accept/reject/skip)
- Store outcomes in Neon PostgreSQL
- Build dataset for ML training

### Task 4: Integration Points
- anti-corruption-orchestrator calls /predict/suggest
- spam-detection requests triage actions
- audit-trail-aggregator logs all feedback

## Phase 4 Preview: ML Model

With 1000+ feedback events, train ML ranker:
- Features: error patterns, user history, context
- Model: XGBoost or LightGBM
- A/B test: rule-based vs ML-based

## Success Metrics
- User acceptance rate > 60%
- Latency < 200ms
- CI fix success rate tracked
- Spam precision > 85%
