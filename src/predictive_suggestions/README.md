# Predictive Suggestions Module

Rule-based recommendation engine for CI failures and security incidents. Provides fallback when the main predictive-propositions-service is unavailable.

## Usage

### Basic Usage

```python
from predictive_suggestions import SuggestionEngine

# Create engine
engine = SuggestionEngine()

# Generate suggestions for CI failure
alert_text = "AssertionError: expected 42 but got 41"
suggestions = engine.generate_suggestions(
    alert_text=alert_text,
    alert_type="CI_FAILURE",
    confidence_threshold=0.7
)

# Rank and filter
ranked = engine.rank_suggestions(suggestions)
filtered = engine.filter_suggestions(ranked, severity='critical')
```

### Batch Processing

```python
alerts = [
    {"text": "AssertionError", "type": "CI_FAILURE"},
    {"text": "phishing attempt", "type": "SECURITY"},
]

results = engine.batch_generate_suggestions(alerts)
for alert_id, suggestions in results.items():
    print(f"Alert {alert_id}: {len(suggestions)} suggestions")
```

## Suggestion Types

### CI Failures
- `TEST_FAILURE_FIX`: Test assertion errors
- `BUILD_ERROR_FIX`: Compilation/syntax errors
- `TIMEOUT_RESOLUTION`: Performance issues
- `DEPENDENCY_UPDATE`: Version conflicts

### Security Incidents
- `PHISHING_ALERT`: Email phishing
- `MALWARE_DETECTION`: File/code threats
- `SOCIAL_ENGINEERING`: Impersonation attempts
- `SCAM_DETECTION`: Financial/prize scams

## Integration with Orchestration Engine

The `predictive_suggestions` module is integrated into `orchestration_engine.py` as a fallback service when the main predictive-propositions-service is unavailable.

## Rule Matching

Rules use regex patterns for matching alert text:

```python
from predictive_suggestions import RuleRepository

repo = RuleRepository()
rule = repo.get_rule('test_failure_001')
match = repo.match_rule(rule, "AssertionError in test")

if match.matched:
    print(f"Matched with confidence: {match.match_score}")
```

## Testing

Run tests:

```bash
pytest tests/test_predictive_suggestions_engine.py
pytest tests/test_predictive_suggestions_rules.py
```
