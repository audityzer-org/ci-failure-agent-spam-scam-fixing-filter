# Predictive Suggestions Module

## Overview
Rule-based recommendation service for CI failures and security incidents.

## Structure
```
src/predictive_suggestions/
├── __init__.py
├── engine.py          # Rule-based suggestion engine
├── rules.py          # Suggestion rules (CI, spam/scam)
├── models.py         # Data models
└── tests/
    ├── test_engine.py
    └── test_rules.py
```

## CI Failure Rules
- **Test Failures**: Suggest rerun, check dependencies, review recent changes
- **Build Errors**: Suggest clean build, check compiler versions, check environment
- **Timeout Failures**: Suggest increase timeout, optimize code, check resource usage
- **Dependency Errors**: Suggest update deps, check compatibility, clear cache

## Spam/Scam Rules
- **Phishing Content**: Flag account verification requests, urgency language
- **Social Engineering**: Detect impersonation, credential harvesting attempts  
- **Malware**: Identify suspicious attachments, links, scripts
- **Scam Patterns**: Detect financial requests, lottery/prize scams

## Usage
```python
from src.predictive_suggestions import SuggestionEngine

engine = SuggestionEngine()

# CI failures
suggestions = engine.suggest_ci_fix(
    failure_type="test_failure",
    error_message="AssertionError: expected True"
)

# Security incidents
suggestions = engine.suggest_security_response(
    incident_type="phishing",
    content="Click here to verify your account"
)
```

## Integration
Works seamlessly with OrchestrationEngine's `apply_proposition()` for automated fixes.

## Future Enhancements
- ML-based rule ranking
- Context-aware suggestions
- Learning from user feedback
- Custom rule builder UI
