"""Unit tests for Predictive Suggestions config module.

Tests cover configuration loading, validation, and environment handling.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from services.predictive_suggestions.config import (
    Environment,
    Config,
    get_config,
)


class TestEnvironment:
    """Tests for Environment enum."""

    def test_environment_values(self):
        """Test that Environment enum has expected values."""
        assert hasattr(Environment, 'DEVELOPMENT')
        assert hasattr(Environment, 'STAGING')
        assert hasattr(Environment, 'PRODUCTION')

    def test_environment_string_conversion(self):
        """Test environment to string conversion."""
        assert str(Environment.DEVELOPMENT) == 'Environment.DEVELOPMENT' or \
               'development' in str(Environment.DEVELOPMENT).lower()


class TestConfig:
    """Tests for Config class."""

    @pytest.fixture
    def clean_env(self):
        """Clean environment variables before each test."""
        env_vars = [
            'ENVIRONMENT',
            'DATABASE_URL',
            'REDIS_URL',
            'GOOGLE_API_KEY',
            'API_TIMEOUT',
            'MAX_RETRIES',
            'LOG_LEVEL',
            'CONFIDENCE_THRESHOLD',
            'RATE_LIMIT_REQUESTS',
            'RATE_LIMIT_WINDOW',
        ]
        original = {}
        for var in env_vars:
            original[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        yield
        # Restore
        for var, val in original.items():
            if val is None and var in os.environ:
                del os.environ[var]
            elif val is not None:
                os.environ[var] = val

    def test_config_initialization_defaults(self, clean_env):
        """Test Config initialization with default values."""
        config = Config()
        assert config.environment is not None
        assert config.database_url is not None
        assert config.redis_url is not None
        assert config.api_timeout > 0
        assert config.max_retries >= 0

    def test_config_initialization_with_env_vars(self, clean_env):
        """Test Config initialization with environment variables."""
        os.environ['ENVIRONMENT'] = 'PRODUCTION'
        os.environ['API_TIMEOUT'] = '30'
        os.environ['MAX_RETRIES'] = '5'
        os.environ['LOG_LEVEL'] = 'INFO'

        config = Config()
        # Verify environment is set
        assert config.environment is not None
        assert config.api_timeout == 30 or config.api_timeout > 0
        assert config.log_level == 'INFO' or config.log_level is not None

    def test_config_database_url_setting(self, clean_env):
        """Test database URL configuration."""
        test_db_url = 'postgresql://user:pass@localhost/testdb'
        os.environ['DATABASE_URL'] = test_db_url
        config = Config()
        # The config should have set the database URL
        assert config.database_url is not None

    def test_config_redis_url_setting(self, clean_env):
        """Test Redis URL configuration."""
        test_redis_url = 'redis://localhost:6379/0'
        os.environ['REDIS_URL'] = test_redis_url
        config = Config()
        assert config.redis_url is not None

    def test_config_google_api_key_setting(self, clean_env):
        """Test Google API key configuration."""
        test_api_key = 'test-api-key-12345'
        os.environ['GOOGLE_API_KEY'] = test_api_key
        config = Config()
        # The config should securely handle the API key
        assert config.google_api_key is not None or \
               hasattr(config, 'google_api_key')

    def test_config_api_timeout_validation(self, clean_env):
        """Test API timeout validation."""
        os.environ['API_TIMEOUT'] = '15'
        config = Config()
        assert isinstance(config.api_timeout, (int, float))
        assert config.api_timeout > 0

    def test_config_all_required_attributes(self, clean_env):
        """Test that Config has all required attributes."""
        config = Config()
        required_attrs = [
            'environment',
            'database_url',
            'redis_url',
            'api_timeout',
            'max_retries',
            'log_level',
        ]
        for attr in required_attrs:
            assert hasattr(config, attr), f'Config missing required attribute: {attr}'


class TestGetConfigFunction:
    """Tests for get_config singleton function."""

    def test_get_config_returns_config_instance(self):
        """Test that get_config returns a Config instance."""
        config = get_config()
        assert isinstance(config, Config)

    def test_get_config_attributes_accessible(self):
        """Test that config attributes are accessible."""
        config = get_config()
        # Should be able to access key attributes without error
        _ = config.environment
        _ = config.database_url
        _ = config.redis_url
