"""Services package initialization."""

# Import subpackages to expose their contents
# Use lazy imports to avoid circular import issues

def __getattr__(name):
    """Lazy import submodules to prevent circular imports."""
    if name == 'predictive_suggestions':
        from . import predictive_suggestions
        return predictive_suggestions
    elif name == 'spam_detection':
        from . import spam_detection
        return spam_detection
    elif name == 'anti_corruption_orchestrator':
        from . import anti_corruption_orchestrator
        return anti_corruption_orchestrator
    elif name == 'audit_trail_aggregator':
        from . import audit_trail_aggregator
        return audit_trail_aggregator
    elif name == 'compliance_validator':
        from . import compliance_validator
        return compliance_validator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'predictive_suggestions',
    'spam_detection',
    'anti_corruption_orchestrator',
    'audit_trail_aggregator',
    'compliance_validator',
]
