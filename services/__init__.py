"""Services package.

This module uses lazy imports to avoid circular import issues
while still allowing Python's import system to discover subpackages.
"""

import importlib
import sys

__all__ = [
    'anti_corruption_orchestrator',
    'audit_trail_aggregator',
    'compliance_validator',
    'predictive_suggestions',
    'spam_detection',
]

_SUBMODULES = {
    'anti_corruption_orchestrator': 'services.anti-corruption-orchestrator',
    'audit_trail_aggregator': 'services.audit-trail-aggregator',
    'compliance_validator': 'services.compliance-validator',
    'predictive_suggestions': 'services.predictive-suggestions',
    'spam_detection': 'services.spam-detection',
}


def __getattr__(name):
    """Lazy load submodules on access."""
    if name in _SUBMODULES:
        submodule_path = _SUBMODULES[name]
        module = importlib.import_module(submodule_path)
        sys.modules[f'services.{name}'] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
