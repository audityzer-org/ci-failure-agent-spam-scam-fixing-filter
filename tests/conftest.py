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
