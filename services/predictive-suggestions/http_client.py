"""HTTP client for external API communication."""
import aiohttp
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from config import config

logger = logging.getLogger(__name__)


class HTTPClient:
    """Async HTTP client for service-to-service communication."""
    
    def __init__(self, timeout: int = 30, retries: int = 3):
        """Initialize HTTP client.
        
        Args:
            timeout: Request timeout in seconds
            retries: Number of retry attempts
        """
        self.timeout = timeout
        self.retries = retries
        self.session = None
    
    async def __aenter__(self):
        """Async context manager enter."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform GET request.
        
        Args:
            url: Request URL
            headers: HTTP headers
            params: Query parameters
            
        Returns:
            Response JSON
        """
        return await self._request('GET', url, headers=headers, params=params)
    
    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform POST request.
        
        Args:
            url: Request URL
            data: Form data
            headers: HTTP headers
            json: JSON body
            
        Returns:
            Response JSON
        """
        return await self._request(
            'POST', url, data=data, headers=headers, json=json
        )
    
    async def put(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform PUT request.
        
        Args:
            url: Request URL
            data: Form data
            headers: HTTP headers
            json: JSON body
            
        Returns:
            Response JSON
        """
        return await self._request(
            'PUT', url, data=data, headers=headers, json=json
        )
    
    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Perform DELETE request.
        
        Args:
            url: Request URL
            headers: HTTP headers
            
        Returns:
            Response JSON
        """
        return await self._request('DELETE', url, headers=headers)
    
    async def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Internal method for making requests with retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional arguments to pass to request
            
        Returns:
            Response JSON
        """
        if not self.session:
            raise RuntimeError("HTTP client session not initialized")
        
        for attempt in range(self.retries):
            try:
                async with self.session.request(method, url, **kwargs) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status >= 500 and attempt < self.retries - 1:
                        logger.warning(
                            f"Server error ({resp.status}) on attempt {attempt + 1}, retrying..."
                        )
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        logger.error(f"HTTP {resp.status} error: {url}")
                        return {'error': f"HTTP {resp.status}", 'url': url}
            except asyncio.TimeoutError:
                if attempt < self.retries - 1:
                    logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error(f"Request timeout after {self.retries} attempts: {url}")
                return {'error': 'Request timeout', 'url': url}
            except Exception as e:
                logger.error(f"Request error: {str(e)}")
                return {'error': str(e), 'url': url}
        
        return {'error': 'Max retries exceeded', 'url': url}


class ServiceClient:
    """Client for inter-service communication."""
    
    def __init__(self):
        """Initialize service client."""
        self.http_client = HTTPClient(
            timeout=config.REQUEST_TIMEOUT,
            retries=3
        )
    
    async def call_service(
        self,
        service_url: str,
        endpoint: str,
        method: str = 'GET',
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call another microservice.
        
        Args:
            service_url: Base service URL
            endpoint: API endpoint
            method: HTTP method
            payload: Request payload
            
        Returns:
            Service response
        """
        url = f"{service_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        async with self.http_client as client:
            if method == 'GET':
                return await client.get(url)
            elif method == 'POST':
                return await client.post(url, json=payload)
            elif method == 'PUT':
                return await client.put(url, json=payload)
            elif method == 'DELETE':
                return await client.delete(url)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return {'error': f'Unsupported method: {method}'}


# Global HTTP client instance
_http_client: Optional[HTTPClient] = None


def get_http_client() -> HTTPClient:
    """Get or create global HTTP client instance."""
    global _http_client
    if _http_client is None:
        _http_client = HTTPClient(
            timeout=config.REQUEST_TIMEOUT,
            retries=3
        )
    return _http_client
