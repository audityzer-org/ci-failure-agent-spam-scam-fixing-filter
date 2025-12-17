"""Redis cache management for Predictive Suggestions Service."""
import json
import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import redis
from redis.exceptions import RedisError, ConnectionError
from .config import config
logger = logging.getLogger(__name__)


class CacheManager:
    """Redis cache management utility."""
    
    def __init__(self, redis_url: Optional[str] = None, ttl: Optional[int] = None):
        """Initialize cache manager.
        
        Args:
            redis_url: Redis connection URL
            ttl: Time-to-live in seconds
        """
        self.redis_url = redis_url or config.REDIS_URL
        self.ttl = ttl or config.CACHE_TTL_SECONDS
        self.prefix = config.CACHE_KEY_PREFIX
        self.client = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish Redis connection."""
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self.client.ping()
            logger.info("Successfully connected to Redis")
        except ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
    
    def _make_key(self, key: str) -> str:
        """Generate prefixed cache key."""
        return f"{self.prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.client:
            return None
        
        try:
            cached = self.client.get(self._make_key(key))
            if cached:
                return json.loads(cached)
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key {key}: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            ttl_seconds = ttl or self.ttl
            self.client.setex(
                self._make_key(key),
                ttl_seconds,
                json.dumps(value)
            )
            return True
        except RedisError as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        if not self.client:
            return False
        
        try:
            self.client.delete(self._make_key(key))
            return True
        except RedisError as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        if not self.client:
            return False
        
        try:
            return bool(self.client.exists(self._make_key(key)))
        except RedisError as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear cache keys matching pattern.
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            Number of keys deleted
        """
        if not self.client:
            return 0
        
        try:
            cursor = 0
            count = 0
            full_pattern = f"{self.prefix}{pattern}"
            
            while True:
                cursor, keys = self.client.scan(cursor, match=full_pattern)
                if keys:
                    count += self.client.delete(*keys)
                if cursor == 0:
                    break
            
            return count
        except RedisError as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment
            
        Returns:
            New value
        """
        if not self.client:
            return 0
        
        try:
            return self.client.incrby(self._make_key(key), amount)
        except RedisError as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0
    
    def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds or None if not found
        """
        if not self.client:
            return None
        
        try:
            ttl = self.client.ttl(self._make_key(key))
            return ttl if ttl > 0 else None
        except RedisError as e:
            logger.warning(f"Cache get_ttl error for key {key}: {e}")
            return None
    
    def close(self) -> None:
        """Close Redis connection."""
        if self.client:
            try:
                self.client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
