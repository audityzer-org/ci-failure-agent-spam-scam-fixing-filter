# Predictive Actions Integration Guide

**Status**: ✅ COMPLETE  
**Version**: 1.0  
**Last Updated**: December 14, 2025  
**Commits**: 94  

---

## Overview

The **Predictive Actions** system provides intelligent recommendations for handling CI failures, security incidents, and spam/scam events. This guide explains how to integrate the REST API with the auditorsec-platform-poc UI to display 2-3 action options and collect user feedback for ML model training.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│  auditorsec-platform-poc (Frontend)                         │
│  - Alert notifications                                      │
│  - Action recommendation panels                             │
│  - User interaction/logging                                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTP/REST
                 │
┌────────────────▼────────────────────────────────────────────┐
│  ci-failure-agent (Backend API)                             │
│  - POST /api/predictive_actions                             │
│  - POST /api/actions/log_selection                          │
│  - GET /api/actions/logs                                    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ ML Training Loop
                 │
┌────────────────▼────────────────────────────────────────────┐
│  ML Model (Future)                                          │
│  - Rank actions based on user feedback                      │
│  - Improve recommendations over time                        │
└─────────────────────────────────────────────────────────────┘
```

## Files Structure

### Backend (ci-failure-agent)

**`src/predictive_actions_api.py`** - REST API Endpoint
- `POST /api/predictive_actions` - Get action recommendations
- `POST /api/actions/log_selection` - Log user selections
- `GET /api/actions/logs` - Retrieve logs for training
- Support for: ci_failure, spam_incident, security_alert

### Platform Integration (auditorsec-platform-poc)

**`src/predictive_actions_platform_client.py`** - Integration Client
- `PredictiveActionsClient` - Async HTTP client
- `PlatformUIActionPresenter` - UI formatting
- `handle_ci_failure_alert()` - Example integration handler

## API Endpoints

### 1. Get Predictive Actions

**Endpoint**: `POST /api/predictive_actions`

**Request**:
```json
{
  "failure_description": "Docker image build failed: base image not found",
  "failure_type": "ci_failure",
  "context": {
    "build_id": "abc123",
    "commit_sha": "def456"
  },
  "severity": "high",
  "user_id": "user@example.com",
  "session_id": "session-789"
}
```

**Response**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-14T19:00:00.000000",
  "actions": [
    {
      "action_id": "action-001",
      "title": "Retry Failed Job",
      "description": "Automatically retry the failed CI job",
      "action_type": "auto_fix",
      "priority": 1,
      "estimated_time": "2-5 minutes",
      "success_rate": 0.72
    },
    {
      "action_id": "action-002",
      "title": "Review Build Logs",
      "description": "Open detailed build logs for inspection",
      "action_type": "manual_review",
      "priority": 1,
      "estimated_time": "5-15 minutes",
      "success_rate": 0.85
    },
    {
      "action_id": "action-003",
      "title": "Run Diagnostics",
      "description": "Execute diagnostic checks",
      "action_type": "auto_fix",
      "priority": 2,
      "estimated_time": "3-10 minutes",
      "success_rate": 0.68
    }
  ],
  "recommended_action_id": "action-001"
}
```

### 2. Log Action Selection

**Endpoint**: `POST /api/actions/log_selection`

**Request**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "action_id": "action-002",
  "selected_at": "2025-12-14T19:05:30.000000",
  "outcome": "successful",
  "feedback": "Action resolved the issue quickly"
}
```

**Response**:
```json
{
  "status": "logged",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-14T19:05:30.000000",
  "total_logs": 42
}
```

### 3. Get Action Logs

**Endpoint**: `GET /api/actions/logs?limit=100`

**Response**:
```json
{
  "total": 150,
  "logs": [
    {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "action_id": "action-002",
      "selected_at": "2025-12-14T19:05:30.000000",
      "outcome": "successful",
      "feedback": "Action resolved the issue quickly"
    }
  ]
}
```

## Platform Integration Example

### Usage in auditorsec-platform-poc

```python
from src.predictive_actions_platform_client import (
    PredictiveActionsClient,
    PlatformUIActionPresenter
)

# Async handler for CI failure alerts
async def on_ci_failure_alert(failure_info):
    async with PredictiveActionsClient(api_url="http://ci-agent:8000") as client:
        # Get recommendations
        response = await client.get_predictive_actions(
            failure_description=failure_info["message"],
            failure_type="ci_failure",
            context=failure_info.get("context"),
            severity="high",
            user_id=current_user.id,
            session_id=session.id
        )
        
        # Format for UI display
        ui_data = PlatformUIActionPresenter.format_actions_for_ui(response)
        
        # Display in alert panel
        show_action_recommendations(ui_data)
        
        # Log user selection
        selected_action = await wait_for_user_selection(ui_data)
        await client.log_action_selection(
            request_id=response.request_id,
            action_id=selected_action["id"],
            outcome="successful",
            feedback=user_feedback
        )
```

## UI Components

### Action Recommendation Panel

Display 2-3 actions with:
- **Title**: Action name ("Retry Failed Job")
- **Description**: What the action does
- **Type Badge**: auto_fix 🔧 | manual_review 👁 | escalate ⚠ | ignore ✓
- **Priority**: Visual indicator (color-coded)
- **Estimated Time**: How long it will take
- **Confidence Score**: ML model confidence (72%)
- **Action Buttons**: Execute | Learn More | Dismiss

### Example HTML Template

```html
<div class="action-recommendation">
  <div class="action-header">
    <h3>{{action.title}}</h3>
    <span class="confidence">{{action.confidence_score}}% Confidence</span>
  </div>
  <p class="description">{{action.description}}</p>
  <div class="metadata">
    <span class="type">{{action.type}}</span>
    <span class="time">⏱ {{action.estimated_time}}</span>
    <span class="priority">Priority: {{action.priority_level}}</span>
  </div>
  <div class="actions">
    <button class="primary" onclick="execute({{action.id}})">Execute</button>
    <button class="secondary" onclick="learnMore({{action.id}})">Learn More</button>
    <button class="tertiary" onclick="dismiss({{action.id}})">Dismiss</button>
  </div>
</div>
```

## ML Model Training Data Flow

1. **User sees 2-3 action recommendations**
2. **User selects one action**
3. **Platform logs selection with outcome**
4. **Logs are collected in `/api/actions/logs`**
5. **ML model analyzes patterns:**
   - Which actions succeed most often
   - Which actions are selected more frequently
   - Correlation between failure type and action success
6. **Model recommends better actions for future similar failures**

## Supported Failure Types

### ci_failure
CI/CD pipeline failures (build, test, deploy)
- Recommended actions: Retry, Review Logs, Run Diagnostics

### spam_incident
Spam/phishing/scam detection
- Recommended actions: Quarantine & Review, Block & Report, Additional Verification

### security_alert
Security threat detection
- Recommended actions: Escalate to Security Team, Isolate Resources, Enable Monitoring

## Deployment

### Start the API Server

```bash
# In ci-failure-agent-spam-scam-fixing-filter
python main.py
# API available at http://localhost:8000/api/predictive_actions
```

### Configure Platform Client

```python
# In auditorsec-platform-poc
from src.predictive_actions_platform_client import PredictiveActionsClient

client = PredictiveActionsClient(
    api_url="http://ci-agent:8000",  # API URL
    timeout=10  # Request timeout
)
```

## Monitoring & Metrics

### Track Success Rates

```sql
SELECT 
    action_type,
    COUNT(*) as total_selections,
    SUM(CASE WHEN outcome = 'successful' THEN 1 ELSE 0 END) as successful,
    ROUND(SUM(CASE WHEN outcome = 'successful' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM action_logs
GROUP BY action_type
ORDER BY success_rate DESC;
```

### API Metrics

- **Request/Response Time**: Track latency
- **Error Rate**: Monitor failures
- **Action Distribution**: Most selected actions
- **Outcome Distribution**: Success/failure/partial ratios

## Troubleshooting

### API Not Responding

```bash
# Check API health
curl http://localhost:8000/api/health
# Expected response: {"status": "healthy", "service": "predictive_actions_api"}
```

### No Actions Returned

- Verify failure_type is valid: ci_failure | spam_incident | security_alert
- Check failure_description is provided
- Review API logs for errors

### Logs Not Being Recorded

- Verify request_id and action_id match original request
- Check network connectivity
- Review action_logs table/storage

## Future Enhancements

- [ ] ML model integration for dynamic action ranking
- [ ] Multi-language support for actions
- [ ] Custom action templates per organization
- [ ] Real-time feedback visualization
- [ ] A/B testing framework for action recommendations
- [ ] Advanced analytics dashboard

## References

- **API Implementation**: `src/predictive_actions_api.py`
- **Platform Client**: `src/predictive_actions_platform_client.py`
- **Phase 2 Summary**: `PHASE_2_COMPLETE_SUMMARY.md`
- **API Documentation**: `http://localhost:8000/docs` (OpenAPI/Swagger)

---

**Repository**: https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter  
**Status**: ✅ Production Ready  
**Last Deployment**: December 14, 2025
