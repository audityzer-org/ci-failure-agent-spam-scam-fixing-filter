# Predictive Propositions Integration Strategy
## CI-Failure-Agent Spam/Scam Filtering System

**Date:** December 14, 2025  
**Status:** Strategic Planning & Design Phase  
**Author:** Igor Romanenko  

---

## Executive Summary

This document defines the integration strategy for **Predictive Propositions Service** within the **CI-Failure-Agent** ecosystem. The service will provide intelligent, context-aware recommendations for:

1. **CI Failure Resolution** - Suggests automated fixes for common CI/CD pipeline failures
2. **Spam/Scam Incident Response** - Recommends triage actions (ignore, report, escalate, manual review)
3. **Workflow Optimization** - Proposes next actions based on historical patterns and ML models

---

## Part 1: Role Definition

### 1.1 Primary Use Cases

#### Use Case 1: CI Failure Analysis & Resolution Propositions

**Trigger:** CI pipeline failure detected  
**Input:**
- Failure type (build, test, deployment, security check)
- Error logs & stack traces
- Repository context
- Historical failure patterns

#### Use Case 2: Spam/Scam Triage Recommendations

**Trigger:** Suspicious activity detected (email, PR comment, webhook)  
**Input:**
- Incident context (type, severity signals)
- Source metadata (IP, domain, user history)
- Content analysis signals
- Compliance risk score

### 1.2 Service Architecture Role

CI-Failure-Agent Microservices integrate with predictive-propositions-service for intelligent recommendations at decision points.

---

## Part 2: Implementation Architecture

### 2.1 New Directory Structure

```
ci-failure-agent-spam-scam-fixing-filter/
services/
+-- predictive-suggestions/  [NEW INTEGRATION]
    +-- __init__.py
    +-- models.py           (Pydantic schemas)
    +-- rules.py            (Rule-based ranker)
    +-- ci_failure_proposer.py
    +-- spam_scam_proposer.py
    +-- logging_pipeline.py
    +-- integration_gateway.py
```

### 2.2 Logging Pipeline for Feedback Tracking

All propositions must be logged with:
- incident_id
- proposition_id
- user_action (accepted/rejected/skipped)
- timestamp
- actual_resolution

This builds dataset for ML ranker training in Phase 3.

---

## Part 3: Integration Points

1. **anti-corruption-orchestrator** - Requests propositions before escalation
2. **spam-detection** - Gets suggested triage actions
3. **compliance-validator** - Validates proposition applicability
4. **audit-trail-aggregator** - Logs all feedback events
