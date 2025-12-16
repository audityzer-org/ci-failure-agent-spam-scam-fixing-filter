"""Pytest configuration for module imports and test discovery."""
import sys
import os
import importlib.util
import pytest
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent

# Add project root to sys.path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add src directory
src_dir = project_root / 'src'
if src_dir.exists() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Add services directory
services_dir = project_root / 'services'
if services_dir.exists() and str(services_dir) not in sys.path:
    sys.path.insert(0, str(services_dir))

# Add tests directory
tests_dir = project_root / 'tests'
if tests_dir.exists() and str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

# Ensure PYTHONPATH is set
os.environ['PYTHONPATH'] = ':'.join([str(project_root), str(src_dir), str(services_dir), str(tests_dir)])

# Use pytest_configure hook to register hyphenated service packages BEFORE collection
def pytest_configure(config):
    """Register hyphenated service packages before pytest collects tests."""
    _register_service_packages()

def _register_service_packages():
    """Register hyphenated service packages in sys.modules."""
    # These packages have hyphens in directory names but need underscores in Python imports
    service_packages = {
        'anti_corruption_orchestrator': 'anti-corruption-orchestrator',
        'audit_trail_aggregator': 'audit-trail-aggregator',
        'compliance_validator': 'compliance-validator',
        'predictive_suggestions': 'predictive-suggestions',
        'spam_detection': 'spam-detection',
    }
    
    services_dir = project_root / 'services'
    for module_base_name, dir_name in service_packages.items():
        # Register both the full package path and simple name
        module_name_underscored = f'services.{module_base_name}'
        module_name_hyphenated = f'services.{dir_name}'  # For external compatibility
        
        module_dir = services_dir / dir_name
        init_file = module_dir / '__init__.py'
        
        if module_dir.exists() and init_file.exists():
            try:
                # Load the module using importlib
                spec = importlib.util.spec_from_file_location(module_name_underscored, init_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    # Register BEFORE executing to avoid circular imports
                    sys.modules[module_name_underscored] = module
                    # Also try to register hyphenated version for test compatibility
                    sys.modules[module_name_hyphenated] = module
                    # Now execute the module
                    spec.loader.exec_module(module)
            except Exception as e:
                # Log but don't fail - services might not be needed
                print(f"Warning: Could not load {module_name_underscored}: {e}", file=sys.stderr)
