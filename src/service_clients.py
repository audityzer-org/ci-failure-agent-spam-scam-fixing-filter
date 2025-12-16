"""Service Client Library - HTTP clients for all microservices with retry logic."""
import aiohttp
import asyncio
from typing import Dict, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

class ServiceClients:
    """Unified HTTP client for all microservices with connection pooling and retries."""
    
    # Service URLs - can be environment variables in production
    SERVICES = {
        'anti_corruption': 'http://localhost:8001',
        'audit_trail': 'http://localhost:8002',
        'compliance': 'http://localhost:8003',
        'spam_detection': 'http://localhost:8004',
        'predictive': 'http://localhost:8005',
    }
    
    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    async def init_session(self):
        """Initialize aiohttp session with connection pooling."""
        if not self.session:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout
            )
    
    async def close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def health_check(self, service: str) -> bool:
        """Check service health with retry logic."""
        await self.init_session()
        url = f"{self.SERVICES.get(service, 'http://localhost:8000')}/health"
        try:
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed for {service}: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def post_request(self, service: str, endpoint: str, data: Dict) -> Optional[Dict]:
        """POST request with retry and error handling."""
        await self.init_session()
        url = f"{self.SERVICES.get(service)}{endpoint}"
        try:
            async with self.session.post(url, json=data) as response:
                if response.status in [200, 201]:
                    return await response.json()
                logger.error(f"POST {endpoint} failed with status {response.status}")
                return None
        except Exception as e:
            logger.error(f"POST request failed: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_request(self, service: str, endpoint: str) -> Optional[Dict]:
        """GET request with retry and error handling."""
        await self.init_session()
        url = f"{self.SERVICES.get(service)}{endpoint}"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"GET {endpoint} failed with status {response.status}")
                return None
        except Exception as e:
            logger.error(f"GET request failed: {e}")
            raise
    
    async def check_all_services(self) -> Dict[str, bool]:
        """Check health of all services."""
        await self.init_session()
        results = {}
        for service in self.SERVICES.keys():
            results[service] = await self.health_check(service)
        return results

# Global client instance
service_clients = ServiceClients()
