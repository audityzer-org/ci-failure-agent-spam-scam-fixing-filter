"""Pytest fixtures and configuration for unit tests."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Generator, Dict, Any
import asyncio
import sys


# Redis mocks
@pytest.fixture
def mock_redis() -> Mock:
    """Mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = 0
    redis_mock.incr.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.ttl.return_value = -2
    redis_mock.keys.return_value = []
    redis_mock.flushdb.return_value = True
    return redis_mock


# PostgreSQL/SQLAlchemy mocks
@pytest.fixture
def mock_db_session() -> Mock:
    """Mock SQLAlchemy database session."""
    session_mock = MagicMock()
    session_mock.query.return_value.filter.return_value.first.return_value = None
    session_mock.query.return_value.filter.return_value.all.return_value = []
    session_mock.query.return_value.all.return_value = []
    session_mock.query.return_value.first.return_value = None
    session_mock.add.return_value = None
    session_mock.commit.return_value = None
    session_mock.rollback.return_value = None
    session_mock.close.return_value = None
    return session_mock


@pytest.fixture
def mock_db_engine() -> Mock:
    """Mock SQLAlchemy database engine."""
    engine_mock = MagicMock()
    engine_mock.connect.return_value = MagicMock()
    engine_mock.dispose.return_value = None
    return engine_mock


# HTTP Client mocks
@pytest.fixture
def mock_http_client() -> Mock:
    """Mock httpx.AsyncClient for HTTP requests."""
    client_mock = MagicMock()
    response_mock = MagicMock()
    response_mock.status_code = 200
    response_mock.json.return_value = {}
    response_mock.text = ""
    client_mock.get = AsyncMock(return_value=response_mock)
    client_mock.post = AsyncMock(return_value=response_mock)
    client_mock.put = AsyncMock(return_value=response_mock)
    client_mock.delete = AsyncMock(return_value=response_mock)
    client_mock.patch = AsyncMock(return_value=response_mock)
    return client_mock


# Google API mocks
@pytest.fixture
def mock_google_api() -> Mock:
    """Mock Google API client."""
    api_mock = MagicMock()
    api_mock.list.return_value = {"items": []}
    api_mock.get.return_value = {}
    api_mock.create.return_value = {"id": "test-id"}
    api_mock.update.return_value = {"id": "test-id"}
    api_mock.delete.return_value = None
    return api_mock


# Email service mocks
@pytest.fixture
def mock_email_service() -> Mock:
    """Mock email service."""
    email_mock = MagicMock()
    email_mock.send.return_value = True
    email_mock.send_async = AsyncMock(return_value=True)
    email_mock.validate_email.return_value = True
    return email_mock


# Configuration fixtures
@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Mock application configuration."""
    return {
        "database_url": "postgresql://test:test@localhost/test_db",
        "redis_url": "redis://localhost:6379/0",
        "google_api_key": "test-api-key",
        "jwt_secret": "test-secret",
        "smtp_server": "localhost",
        "smtp_port": 587,
        "debug": True,
        "testing": True,
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables."""
    env_vars = {
        "DATABASE_URL": "postgresql://test:test@localhost/test_db",
        "REDIS_URL": "redis://localhost:6379/0",
        "GOOGLE_API_KEY": "test-api-key",
        "JWT_SECRET": "test-secret",
        "SMTP_SERVER": "localhost",
        "SMTP_PORT": "587",
        "DEBUG": "true",
        "ENVIRONMENT": "testing",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


# Async fixtures
@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Context manager fixtures
@pytest.fixture
def mock_context_manager() -> Mock:
    """Mock context manager for resource management."""
    ctx_mock = MagicMock()
    ctx_mock.__enter__.return_value = MagicMock()
    ctx_mock.__exit__.return_value = False
    return ctx_mock


# Auto-use fixtures for all tests
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, mock_env_vars):
    """Set up test environment variables for all tests."""
    pass


# Markers for test categorization
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


# Mock validators for Pydantic models
@pytest.fixture
def mock_validators_module(monkeypatch):
    """Mock the validators module to provide flexible Pydantic models."""
    from datetime import datetime
    from unittest.mock import MagicMock
    
    # Create mock validator classes that accept flexible input
    class MockValidationResult:
        def __init__(self, is_valid=True, errors=None):
            self.is_valid = is_valid
            self.errors = errors or []
    
    class MockPredictionRequestValidator:
        def __init__(self, **kwargs):
            self.failure_pattern = kwargs.get('failure_pattern', '')
            self.historical_data = kwargs.get('historical_data', {})
        
        def validate(self, data):
            return MockValidationResult(is_valid=True)
    
    class MockSuggestionResponseValidator:
        def __init__(self, **kwargs):
            self.suggestion_id = kwargs.get('suggestion_id', 'test-id')
            self.prediction_confidence = kwargs.get('prediction_confidence', 0.5)
            self.recommended_actions = kwargs.get('recommended_actions', [])
            self.expected_impact = kwargs.get('expected_impact', 'MEDIUM')
            self.preventive_measures = kwargs.get('preventive_measures', [])
            self.created_at = kwargs.get('created_at', datetime.now())
        
        def validate(self, data):
            return MockValidationResult(is_valid=True)
    
    class MockInputValidator:
        def validate_string(self, value):
            return MockValidationResult(is_valid=True)
        
        def validate_numeric(self, value):
            return MockValidationResult(is_valid=True)
        
        def validate_list(self, value):
            return MockValidationResult(is_valid=True)
    
    class MockParameterSanitizer:
        def sanitize_string(self, value):
            return str(value).strip()
        
        def sanitize_numeric(self, value):
            try:
                return float(value)
            except:
                return None
        
        def sanitize_email(self, value):
            return str(value).lower()
    
    # Mock ImpactLevel enum
    class MockImpactLevel:
        LOW = 'low'
        MEDIUM = 'medium'
        HIGH = 'high'
        CRITICAL = 'critical'
    
    # Monkeypatch the imports
    validators_mock = MagicMock()
    validators_mock.ValidationResult = MockValidationResult
    validators_mock.PredictionRequestValidator = MockPredictionRequestValidator
    validators_mock.SuggestionResponseValidator = MockSuggestionResponseValidator
    validators_mock.InputValidator = MockInputValidator
    validators_mock.ParameterSanitizer = MockParameterSanitizer
    validators_mock.ImpactLevel = MockImpactLevel
    
    monkeypatch.setitem(sys.modules, 'services.predictive_suggestions.validators', validators_mock)
    
    return validators_mock


# Pytest option to auto-use validators mock
@pytest.fixture(autouse=True)
def inject_validators_mock(mock_validators_module):
    """Auto-inject validators mock for all tests."""
    pass
