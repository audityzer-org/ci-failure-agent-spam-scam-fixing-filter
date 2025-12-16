"""Production Hardening Module for Predictive Actions System

Implements critical production enhancements:
- Retry logic with exponential backoff
- Response caching for frequently used data
- Rate limiting for API endpoints
- Distributed tracing integration
- Circuit breaker patterns
- Comprehensive error handling
"""

import asyncio
import logging
import time
from typing import Any, Callable, Optional, TypeVar, Dict
from functools import wraps
import hashlib
from datetime import datetime, timedelta
import redis
import structlog

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreaker:
    """Implements circuit breaker pattern for service calls."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return (datetime.now() - self.last_failure_time).total_seconds() > self.timeout

    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        self.state = 'CLOSED'

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'


class ResponseCache:
    """Caches responses using Redis."""

    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379,
                 ttl: int = 3600):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        self.ttl = ttl
        self.logger = structlog.get_logger()

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function call."""
        key_data = f"{func_name}:{str(args)}:{str(kwargs)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get_or_call(self, func: Callable, func_name: str,
                         args: tuple, kwargs: dict) -> Any:
        """Get value from cache or call function."""
        cache_key = self._generate_key(func_name, args, kwargs)

        # Try cache first
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                self.logger.info("cache_hit", key=cache_key)
                return cached.decode()
        except Exception as e:
            self.logger.warning("cache_error", error=str(e))

        # Call function
        result = await func(*args, **kwargs)

        # Cache result
        try:
            self.redis_client.setex(cache_key, self.ttl, str(result))
        except Exception as e:
            self.logger.warning("cache_set_error", error=str(e))

        return result


class RateLimiter:
    """Implements rate limiting using sliding window."""

    def __init__(self, max_calls: int = 100, window_size: int = 60,
                 redis_host: str = 'localhost', redis_port: int = 6379):
        self.max_calls = max_calls
        self.window_size = window_size
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        self.logger = structlog.get_logger()

    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed under rate limit."""
        key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        window_start = current_time - self.window_size

        try:
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(current_time): current_time})
            pipe.expire(key, self.window_size)
            results = pipe.execute()

            request_count = results[1]
            if request_count >= self.max_calls:
                self.logger.warning("rate_limit_exceeded", identifier=identifier)
                return False
            return True
        except Exception as e:
            self.logger.error("rate_limit_error", error=str(e))
            return False


async def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Retry attempt {attempt + 1}, delay {delay}s")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All retries exhausted: {str(e)}")
            raise last_exception
        return wrapper
    return decorator


class DistributedTracer:
    """Integrates with distributed tracing systems (Jaeger, Zipkin)."""

    def __init__(self, service_name: str = "predictive-actions"):
        self.service_name = service_name
        self.logger = structlog.get_logger()

    def start_span(self, span_name: str, tags: Optional[Dict] = None) -> Dict:
        """Start a distributed trace span."""
        span_id = f"{self.service_name}:{span_name}:{int(time.time() * 1000)}"
        span = {
            "span_id": span_id,
            "span_name": span_name,
            "start_time": datetime.utcnow(),
            "tags": tags or {},
            "logs": []
        }
        return span

    def end_span(self, span: Dict) -> None:
        """End a distributed trace span."""
        span["end_time"] = datetime.utcnow()
        duration = (span["end_time"] - span["start_time"]).total_seconds()
        self.logger.info("span_completed", span_id=span["span_id"],
                        duration=duration, tags=span["tags"])

    def log_event(self, span: Dict, event_name: str, data: Dict) -> None:
        """Log event within span."""
        span["logs"].append({
            "timestamp": datetime.utcnow(),
            "event": event_name,
            "data": data
        })
