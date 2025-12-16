"""Services package."""
# Subpackages are available for direct import

# Explicitly import subpackages to make them discoverable
try:
    from . import predictive_suggestions
except ImportError:
    pass

try:
    from . import spam_detection
except ImportError:
    pass

try:
    from . import anti_corruption_orchestrator
except ImportError:
    pass

try:
    from . import audit_trail_aggregator
except ImportError:
    pass

try:
    from . import compliance_validator
except ImportError:
    pass
