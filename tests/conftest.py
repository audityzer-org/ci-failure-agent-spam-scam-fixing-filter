"""Pytest configuration for module imports and test discovery."""
import sys
import os
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent

# Add project root to sys.path (for src and services modules)
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

# Ensure PYTHONPATH is set correctly for subprocesses
os.environ['PYTHONPATH'] = ':'.join([str(project_root), str(src_dir), str(services_dir), str(tests_dir)])

# Register hyphenated service packages in sys.modules for pytest discovery
service_packages = {
    'services.anti_corruption_orchestrator': services_dir / 'anti-corruption-orchestrator',
    'services.audit_trail_aggregator': services_dir / 'audit-trail-aggregator',
    'services.compliance_validator': services_dir / 'compliance-validator',
    'services.predictive_suggestions': services_dir / 'predictive-suggestions',
    'services.spam_detection': services_dir / 'spam-detection',
}

for module_name, module_path in service_packages.items():
    if module_path.exists() and module_name not in sys.modules:
        init_file = module_path / '__init__.py'
        if init_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(module_name, init_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
            except Exception:
                pass
