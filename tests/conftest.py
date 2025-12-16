"""Pytest configuration for test discovery and module importing."""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add src directory to path
src_dir = project_root / 'src'
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

# Add services directory to path
services_dir = project_root / 'services'
if services_dir.exists():
    sys.path.insert(0, str(services_dir))

# Add tests directory to path
tests_dir = project_root / 'tests'
if tests_dir.exists():
    sys.path.insert(0, str(tests_dir))
