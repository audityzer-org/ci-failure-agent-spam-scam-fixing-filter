"""Request and response handlers for Predictive Suggestions Service."""
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from functools import wraps
from fastapi import Request, Response
import json
from validators import InputValidator, ParameterSanitizer
from cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class RequestHandler:
    """Handler for incoming requests."""
    
    @staticmethod
    def extract_request_info(request: Request) -> Dict[str, Any]:
        """Extract and log request information.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Request information dictionary
        """
        return {
            'method': request.method,
            'path': request.url.path,
            'query_params': dict(request.query_params),
            'headers': dict(request.headers),
            'client': f"{request.client.host}:{request.client.port}" if request.client else None,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def parse_json_body(request: Request) -> Dict[str, Any]:
        """Parse and validate JSON request body.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Parsed JSON body
        """
        try:
            body = await request.json()
            # Sanitize the body
            return ParameterSanitizer.sanitize_dict(body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON body: {e}")
            return {}


class ResponseHandler:
    """Handler for outgoing responses."""
    
    @staticmethod
    def success_response(
        data: Any,
        status_code: int = 200,
        message: str = "Success"
    ) -> Dict[str, Any]:
        """Create a success response.
        
        Args:
            data: Response data
            status_code: HTTP status code
            message: Success message
            
        Returns:
            Response dictionary
        """
        return {
            'status': 'success',
            'code': status_code,
            'message': message,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def error_response(
        error: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create an error response.
        
        Args:
            error: Error message
            status_code: HTTP status code
            details: Additional error details
            
        Returns:
            Error response dictionary
        """
        return {
            'status': 'error',
            'code': status_code,
            'message': error,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def paginated_response(
        data: list,
        total: int,
        page: int,
        page_size: int,
        message: str = "Success"
    ) -> Dict[str, Any]:
        """Create a paginated response.
        
        Args:
            data: Response data list
            total: Total number of items
            page: Current page number
            page_size: Items per page
            message: Success message
            
        Returns:
            Paginated response dictionary
        """
        return {
            'status': 'success',
            'message': message,
            'data': data,
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            },
            'timestamp': datetime.utcnow().isoformat()
        }


class RateLimiter:
    """Simple rate limiter using Redis."""
    
    def __init__(self, requests_per_minute: int = 60):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_minute = requests_per_minute
        self.cache = get_cache_manager()
    
    def get_rate_limit_key(self, client_id: str) -> str:
        """Generate rate limit key.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Rate limit key
        """
        return f"rate_limit:{client_id}"
    
    def is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if rate limited, False otherwise
        """
        key = self.get_rate_limit_key(client_id)
        count = self.cache.client.get(key)
        
        if count is None:
            self.cache.set(key, 1, ttl=60)
            return False
        
        count = int(count)
        if count >= self.requests_per_minute:
            return True
        
        self.cache.increment(key, 1)
        return False


def rate_limit(requests_per_minute: int = 60):
    """Decorator for rate limiting endpoints.
    
    Args:
        requests_per_minute: Maximum requests per minute
    """
    limiter = RateLimiter(requests_per_minute)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get client IP
            client_ip = request.client.host if request.client else "unknown"
            
            if limiter.is_rate_limited(client_ip):
                logger.warning(f"Rate limit exceeded for client: {client_ip}")
                return ResponseHandler.error_response(
                    "Rate limit exceeded",
                    status_code=429,
                    details={'retry_after': 60}
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def validate_request(validator_func: Callable):
    """Decorator for request validation.
    
    Args:
        validator_func: Validation function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                body = await RequestHandler.parse_json_body(request)
                result = validator_func(body)
                
                if hasattr(result, 'is_valid') and not result.is_valid:
                    logger.warning(f"Validation failed: {result.errors}")
                    return ResponseHandler.error_response(
                        "Validation failed",
                        status_code=422,
                        details={'errors': result.errors}
                    )
            except Exception as e:
                logger.error(f"Request validation error: {e}")
                return ResponseHandler.error_response(
                    "Invalid request format",
                    status_code=400
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


class LoggingMiddleware:
    """Middleware for request/response logging."""
    
    def __init__(self, app):
        """Initialize logging middleware.
        
        Args:
            app: FastAPI application
        """
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        """Process request and response.
        
        Args:
            request: Request object
            call_next: Next handler
            
        Returns:
            Response object
        """
        # Log request
        request_info = RequestHandler.extract_request_info(request)
        logger.info(f"Incoming request: {request_info}")
        
        try:
            response = await call_next(request)
            logger.info(f"Response status: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return Response(
                content=json.dumps(
                    ResponseHandler.error_response("Internal server error", 500)
                ),
                status_code=500,
                media_type="application/json"
            )
