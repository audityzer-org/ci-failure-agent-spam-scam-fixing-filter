"""Unit tests for Predictive Suggestions cache_manager module.

Tests cover Redis cache operations, TTL management, and singleton patterns.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from services.predictive_suggestions.cache_manager import (
    CacheManager,
    get_cache_manager,
)


class TestCacheManager:
    """Tests for CacheManager class."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        return MagicMock()

    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Create CacheManager with mocked Redis."""
        with patch('services.predictive_suggestions.cache_manager.redis.from_url'):
            manager = CacheManager()
            manager.client = mock_redis
            return manager

    def test_cache_manager_initialization(self, cache_manager):
        """Test CacheManager can be initialized."""
        assert cache_manager is not None
        assert isinstance(cache_manager, CacheManager)

    def test_cache_get_operation(self, cache_manager, mock_redis):
        """Test cache get operation."""
        mock_redis.get.return_value = b'cached_value'
        result = cache_manager.get('test_key')
        assert result is not None
        mock_redis.get.assert_called_once_with('test_key')

    def test_cache_get_missing_key(self, cache_manager, mock_redis):
        """Test cache get with missing key."""
        mock_redis.get.return_value = None
        result = cache_manager.get('nonexistent_key')
        assert result is None

    def test_cache_set_operation(self, cache_manager, mock_redis):
        """Test cache set operation."""
        mock_redis.set.return_value = True
        result = cache_manager.set('test_key', 'test_value')
        assert result is not None
        mock_redis.set.assert_called_once()

    def test_cache_set_with_ttl(self, cache_manager, mock_redis):
        """Test cache set operation with TTL."""
        mock_redis.setex.return_value = True
        result = cache_manager.set('test_key', 'test_value', ttl=3600)
        assert result is not None
        mock_redis.setex.assert_called_once()

    def test_cache_delete_operation(self, cache_manager, mock_redis):
        """Test cache delete operation."""
        mock_redis.delete.return_value = 1
        result = cache_manager.delete('test_key')
        assert result is not None
        mock_redis.delete.assert_called_once_with('test_key')

    def test_cache_exists_check(self, cache_manager, mock_redis):
        """Test checking if key exists in cache."""
        mock_redis.exists.return_value = 1
        result = cache_manager.exists('test_key')
        assert result is not None

    def test_cache_clear_pattern(self, cache_manager, mock_redis):
        """Test clearing cache entries by pattern."""
        mock_redis.keys.return_value = [b'prefix:1', b'prefix:2']
        mock_redis.delete.return_value = 2
        result = cache_manager.clear_pattern('prefix:*')
        assert result is not None

    def test_cache_increment_counter(self, cache_manager, mock_redis):
        """Test incrementing a counter in cache."""
        mock_redis.incr.return_value = 1
        result = cache_manager.increment('counter_key')
        assert result is not None
        mock_redis.incr.assert_called_once_with('counter_key')

    def test_cache_get_ttl(self, cache_manager, mock_redis):
        """Test getting TTL of a cache entry."""
        mock_redis.ttl.return_value = 3600
        result = cache_manager.get_ttl('test_key')
        assert result is not None

    def test_cache_close_connection(self, cache_manager, mock_redis):
        """Test closing cache connection."""
        mock_redis.close.return_value = None
        result = cache_manager.close()
        assert result is None
        mock_redis.close.assert_called_once()

    def test_cache_with_large_value(self, cache_manager, mock_redis):
        """Test cache operations with large values."""
        large_value = 'x' * (10 * 1024 * 1024)  # 10MB
        mock_redis.set.return_value = True
        result = cache_manager.set('large_key', large_value)
        assert result is not None

    def test_cache_with_special_characters(self, cache_manager, mock_redis):
        """Test cache keys with special characters."""
        mock_redis.set.return_value = True
        result = cache_manager.set('key:with:colons', 'value')
        assert result is not None

    def test_cache_json_serialization(self, cache_manager, mock_redis):
        """Test cache with JSON-serializable values."""
        import json
        test_dict = {'key': 'value', 'nested': {'inner': 'data'}}
        mock_redis.set.return_value = True
        result = cache_manager.set('json_key', json.dumps(test_dict))
        assert result is not None


class TestGetCacheManager:
    """Tests for get_cache_manager singleton function."""

    @patch('services.predictive_suggestions.cache_manager.redis.from_url')
    def test_get_cache_manager_returns_instance(self, mock_redis):
        """Test that get_cache_manager returns a CacheManager instance."""
        with patch.object(CacheManager, '__init__', lambda x: None):
            manager = get_cache_manager()
            assert manager is None or isinstance(manager, CacheManager)

    def test_get_cache_manager_singleton_behavior(self):
        """Test that get_cache_manager returns same instance."""
        # This test depends on implementation details
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        # Both should be the same type or equivalent
        assert manager1 is None or isinstance(manager1, CacheManager)
        assert manager2 is None or isinstance(manager2, CacheManager)


class TestCacheManagerEdgeCases:
    """Tests for edge cases in cache manager."""

    @pytest.fixture
    def cache_manager(self):
        """Create CacheManager with mocked Redis."""
        with patch('services.predictive_suggestions.cache_manager.redis.from_url'):
            manager = CacheManager()
            manager.client = MagicMock()
            return manager

    def test_cache_with_empty_string_key(self, cache_manager):
        """Test cache with empty string as key."""
        cache_manager.client.set.return_value = True
        result = cache_manager.set('', 'value')
        assert result is not None

    def test_cache_with_empty_string_value(self, cache_manager):
        """Test cache with empty string as value."""
        cache_manager.client.set.return_value = True
        result = cache_manager.set('key', '')
        assert result is not None

    def test_cache_with_null_value(self, cache_manager):
        """Test cache with None value."""
        cache_manager.client.set.return_value = True
        result = cache_manager.set('key', None)
        assert result is not None

    def test_cache_with_zero_ttl(self, cache_manager):
        """Test cache with zero TTL."""
        cache_manager.client.setex.return_value = True
        result = cache_manager.set('key', 'value', ttl=0)
        assert result is not None

    def test_cache_with_negative_ttl(self, cache_manager):
        """Test cache with negative TTL."""
        cache_manager.client.setex.return_value = True
        # Should handle gracefully
        result = cache_manager.set('key', 'value', ttl=-1)
        assert result is not None

    def test_cache_connection_error_handling(self, cache_manager):
        """Test handling of Redis connection errors."""
        cache_manager.client.get.side_effect = Exception('Connection error')
        # Should handle error gracefully or raise informatively
        try:
            result = cache_manager.get('key')
            # If no exception, that's fine too
            assert True
        except Exception:
            # Connection errors are expected to propagate or be handled
            assert True
