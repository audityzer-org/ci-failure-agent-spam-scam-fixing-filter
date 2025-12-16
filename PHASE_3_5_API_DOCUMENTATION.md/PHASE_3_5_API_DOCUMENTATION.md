# Phase 3.5: API Documentation & ML Training Data Structure

## Overview

Comprehensive API documentation for the Predictive Propositions orchestration engine with method signatures, usage examples, and data structures for ML model training.

## Table of Contents

1. [Core API Methods](#core-api-methods)
2. [Data Structures](#data-structures)
3. [Usage Examples](#usage-examples)
4. [ML Training Data](#ml-training-data)
5. [Error Handling](#error-handling)

---

## Core API Methods

### 1. `process_alert(alert: Alert) -> Dict[str, Any]`

**Description**: Main entry point for processing incoming alerts and fetching predictive propositions.

**Parameters**:
- `alert` (Alert): The alert object containing detection data
  - `id` (str): Unique alert identifier
  - `type` (AlertType): Type of alert (CI_FAILURE, SPAM_INCIDENT, SCAM_INCIDENT, SECURITY_ALERT)
  - `severity` (int): Severity level (1-10)
  - `description` (str): Detailed description of the issue
  - `metadata` (dict): Additional context information

**Returns**: Dictionary containing:
```python
{
    "request_id": str,           # Unique request tracking ID
    "alert_id": str,            # Original alert ID
    "alert_type": str,          # Type of alert
    "status": str,              # Processing status
    "propositions": List[PredictiveProposition],  # Recommended actions
    "proposition_count": int,   # Number of propositions
    "timestamp": str            # ISO format timestamp
}
```

**Example**:
```python
alert = Alert(
    id="ci-fail-001",
    type=AlertType.CI_FAILURE,
    severity=7,
    description="Unit tests failed in main branch",
    metadata={"repo": "project-x", "branch": "main"}
)

result = await engine.process_alert(alert)
propositions = result["propositions"]
```

---

### 2. `apply_proposition(proposition_id: str, decision: PropositionDecision) -> Dict[str, Any]`

**Description**: Apply a user's decision to a recommended proposition.

**Parameters**:
- `proposition_id` (str): ID of the proposition
- `decision` (PropositionDecision): User's decision (ACCEPTED, REJECTED, DEFERRED)

**Returns**: Execution result with status

**Example**:
```python
result = await engine.apply_proposition(
    proposition_id="prop-123",
    decision=PropositionDecision.ACCEPTED
)
```

---

### 3. `get_proposition_logs(alert_id: Optional[str] = None, limit: int = 100) -> List[PropositionLog]`

**Description**: Retrieve proposition history for ML training data analysis.

**Parameters**:
- `alert_id` (optional): Filter by specific alert
- `limit` (int): Maximum number of records to return

**Returns**: List of PropositionLog entries

**Example**:
```python
logs = await engine.get_proposition_logs(limit=50)
for log in logs:
    print(f"Alert {log.alert_id}: User chose {log.user_decision}")
```

---

### 4. `_fetch_predictive_propositions_with_retry(alert: Alert, request_id: str) -> List[PredictiveProposition]`

**Description**: Fetch propositions with automatic retry and circuit breaker protection.

**Features**:
- Exponential backoff retry logic (1s, 2s, 4s delays)
- Circuit breaker pattern for fault tolerance
- Graceful degradation when service unavailable
- Comprehensive error logging

**Parameters**:
- `alert` (Alert): The alert to get propositions for
- `request_id` (str): Request tracking ID

**Returns**: List of PredictiveProposition objects (empty list on complete failure)

---

## Data Structures

### Alert Dataclass
```python
@dataclass
class Alert:
    id: str
    type: AlertType
    severity: int  # 1-10 scale
    description: str
    metadata: dict
```

### PredictiveProposition Dataclass
```python
@dataclass
class PredictiveProposition:
    id: str
    alert_id: str
    action_type: str  # "AUTO_FIX", "REVIEW", "ESCALATE"
    confidence: float  # 0.0 - 1.0
    recommendation: str
    execution_details: dict
```

### PropositionDecision Enum
```python
class PropositionDecision(Enum):
    ACCEPTED = "accepted"      # User approved action
    REJECTED = "rejected"      # User rejected action
    DEFERRED = "deferred"      # User deferred decision
```

### PropositionLog Dataclass (ML Training)
```python
@dataclass
class PropositionLog:
    alert_id: str
    request_id: str
    proposition_id: str
    user_decision: PropositionDecision
    action_outcome: Optional[str]  # Result after execution
    timestamp: datetime
    
    # ML Features for ranker training
    alert_severity: int
    alert_type: str
    proposition_confidence: float
    execution_time_ms: float
```

---

## Usage Examples

### Complete Workflow
```python
import asyncio
from src.orchestration_engine import OrchestrationEngine, Alert, AlertType, PropositionDecision

async def main():
    # Initialize engine
    engine = OrchestrationEngine(
        predictive_service_url="http://localhost:8001"
    )
    
    # Create alert
    alert = Alert(
        id="security-001",
        type=AlertType.SECURITY_ALERT,
        severity=9,
        description="Unauthorized access attempt detected",
        metadata={"source_ip": "192.168.1.100"}
    )
    
    # Process alert and get propositions
    result = await engine.process_alert(alert)
    propositions = result["propositions"]
    
    if propositions:
        # User approves first proposition
        best_prop = propositions[0]
        await engine.apply_proposition(
            proposition_id=best_prop.id,
            decision=PropositionDecision.ACCEPTED
        )
    
    # Query logs for ML training
    logs = await engine.get_proposition_logs(limit=100)
    print(f"Collected {len(logs)} training samples")

asyncio.run(main())
```

---

## ML Training Data

### PropositionLog Structure for ML Ranker

The `PropositionLog` contains all features needed to train a ML model that ranks proposition quality:

**Features**:
- Alert characteristics (severity, type)
- Proposition confidence score
- User decision (feedback label)
- Action outcome (execution result)
- Execution time
- Timestamp for temporal patterns

**Usage for ML**:
```python
# Extract training features from logs
training_data = []
for log in logs:
    features = {
        "severity": log.alert_severity,
        "alert_type_encoded": encode_alert_type(log.alert_type),
        "confidence": log.proposition_confidence,
        "execution_time": log.execution_time_ms,
    }
    label = 1 if log.user_decision == PropositionDecision.ACCEPTED else 0
    training_data.append((features, label))

# Train ranker model
model.fit(training_data)
```

---

## Error Handling

### Retry Policy

Configurable retry mechanism with exponential backoff:

```python
from src.orchestration_engine import RetryPolicy

policy = RetryPolicy(
    max_retries=3,
    initial_delay=1.0,
    exponential_base=2.0,
    max_delay=60.0,
    jitter=True
)

# Delays: 1s, 2s, 4s (with jitter applied)
```

### Circuit Breaker

Fault tolerance pattern prevents cascading failures:

```python
from src.orchestration_engine import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    success_threshold=2,
    timeout=60.0
)

# States: CLOSED (normal) -> OPEN (failed) -> HALF_OPEN (recovering) -> CLOSED
```

### Graceful Degradation

When propositions service fails, system returns gracefully:

```python
# On service unavailable:
# 1. Returns empty propositions list []
# 2. Logs error with request ID for debugging
# 3. Alert still processed successfully
# 4. User notified about limited recommendations
```

---

## Performance Considerations

- **Timeout**: 30 seconds for HTTP calls
- **Retry delays**: Exponential backoff prevents overwhelming failed service
- **Circuit breaker**: Stops attempting calls after 5 consecutive failures
- **Recovery**: Attempts recovery after 60-second timeout

## Monitoring & Observability

All operations are logged with:
- Request IDs for tracing
- Timestamps for performance analysis
- Decision tracking for ML training
- Error details for debugging

Logs can be queried for:
- API performance metrics
- Error rate analysis
- ML training data collection
- User behavior patterns
