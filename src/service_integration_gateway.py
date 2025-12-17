"""Unified Service Integration Gateway - Coordinates all microservices.

Integrates:
- Anti-Corruption Orchestrator (detection & remediation)
- Spam Detection Service (spam/scam identification)
- Compliance Validator (compliance enforcement)
- Audit Trail Aggregator (centralized logging)

Provides:
- Service discovery & health checks
- Inter-service communication
- Event routing & orchestration
- Distributed transaction management
- Service mesh monitoring
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
import httpx
import redis.asyncio as redis
from task_queue import TaskQueue, TaskPriority, TaskStatus
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from circuitbreaker import circuit
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize FastAPI
app = FastAPI(
    title="Service Integration Gateway",
    description="Unified orchestration layer for all microservices",
    version="1.0.0"
)

# Service Configuration
class ServiceConfig(BaseModel):
    """Service configuration model."""
    name: str
    url: str
    health_check_path: str = "/health"
    timeout: int = 30
    retries: int = 3
    priority: int = 1  # Higher = more important

class ServiceStatus(str, Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ServiceHealth:
    """Service health information."""
    name: str
    status: ServiceStatus
    last_check: str
    response_time_ms: float
    error_rate: float = 0.0

class ServiceRegistry:
    """Manages service discovery and health monitoring."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.services: Dict[str, ServiceConfig] = {}
        self.health_status: Dict[str, ServiceHealth] = {}
        
    async def register_service(self, config: ServiceConfig) -> None:
        """Register a new service."""
        self.services[config.name] = config
        await self.redis.hset(
            "services:registry",
            config.name,
            json.dumps(asdict(config))
        )
        logger.info(f"Service registered", service=config.name, url=config.url)
    
    async def deregister_service(self, service_name: str) -> None:
        """Deregister a service."""
        del self.services[service_name]
        await self.redis.hdel("services:registry", service_name)
        logger.info(f"Service deregistered", service=service_name)
    
    async def get_service(self, service_name: str) -> Optional[ServiceConfig]:
        """Get service configuration."""
        return self.services.get(service_name)
    
    async def list_services(self) -> List[ServiceConfig]:
        """List all registered services."""
        return list(self.services.values())
    
    async def health_check_all(self) -> Dict[str, ServiceHealth]:
        """Check health of all services."""
        tasks = [
            self._health_check_service(service)
            for service in self.services.values()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_map = {}
        for result in results:
            if isinstance(result, ServiceHealth):
                health_map[result.name] = result
                self.health_status[result.name] = result
        
        return health_map
    
    async def _health_check_service(self, service: ServiceConfig) -> ServiceHealth:
        """Check individual service health."""
        try:
            async with httpx.AsyncClient(timeout=service.timeout) as client:
                start = datetime.utcnow()
                response = await client.get(
                    f"{service.url}{service.health_check_path}"
                )
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                
                status = ServiceStatus.HEALTHY if response.status_code == 200 else ServiceStatus.DEGRADED
                
                return ServiceHealth(
                    name=service.name,
                    status=status,
                    last_check=datetime.utcnow().isoformat(),
                    response_time_ms=elapsed
                )
        except Exception as e:
            logger.error(f"Health check failed", service=service.name, error=str(e))
            return ServiceHealth(
                name=service.name,
                status=ServiceStatus.UNHEALTHY,
                last_check=datetime.utcnow().isoformat(),
                response_time_ms=0
            )

class EventOrchestrator:
    """Orchestrates events across services."""
    
    def __init__(self, redis_client: redis.Redis, registry: ServiceRegistry):
        self.redis = redis_client
        self.registry = registry
        self.event_handlers: Dict[str, List[callable]] = {}
    
    async def publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish event to all subscribed services."""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # Store in event stream
        await self.redis.xadd(
            f"events:{event_type}",
            {"payload": json.dumps(event)}
        )
        
        # Execute local handlers
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(event) if asyncio.iscoroutinefunction(handler) else handler(event)
                except Exception as e:
                    logger.error(f"Event handler failed", event_type=event_type, error=str(e))
    
    async def subscribe_event(self, event_type: str, handler: callable) -> None:
        """Subscribe to event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.info(f"Event handler registered", event_type=event_type)
    
    async def forward_to_service(self, service_name: str, endpoint: str, method: str = "POST", data: Optional[Dict] = None) -> Any:
        """Forward request to specific service with circuit breaker."""
        service = await self.registry.get_service(service_name)
        if not service:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        
        url = f"{service.url}{endpoint}"
        
        @circuit(failure_threshold=5, recovery_timeout=60)
        async def call_service():
            async with httpx.AsyncClient(timeout=service.timeout) as client:
                if method.upper() == "POST":
                    return await client.post(url, json=data)
                elif method.upper() == "GET":
                    return await client.get(url)
                elif method.upper() == "PUT":
                    return await client.put(url, json=data)
                elif method.upper() == "DELETE":
                    return await client.delete(url)
        
        try:
            response = await call_service()
            return response.json() if response.status_code < 300 else None
        except Exception as e:
            logger.error(f"Service call failed", service=service_name, endpoint=endpoint, error=str(e))
            raise

# Global instances
redis_client = None
service_registry = None
event_orchestrator = None

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    global redis_client, service_registry, event_orchestrator
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = await redis.from_url(redis_url)
    service_registry = ServiceRegistry(redis_client)
    event_orchestrator = EventOrchestrator(redis_client, service_registry)
        task_queue = TaskQueue(redis_client=redis_client, queue_name='service-integration')
    logger.info("TaskQueue initialized for service integration")
    
    # Register all services
    services = [
        ServiceConfig(
            name="anti-corruption-orchestrator",
            url=os.getenv("ANTI_CORRUPTION_URL", "http://localhost:8001")
        ),
        ServiceConfig(
            name="spam-detection",
            url=os.getenv("SPAM_DETECTION_URL", "http://localhost:8002")
        ),
        ServiceConfig(
            name="compliance-validator",
            url=os.getenv("COMPLIANCE_VALIDATOR_URL", "http://localhost:8003")
        ),
        ServiceConfig(
            name="audit-trail-aggregator",
            url=os.getenv("AUDIT_TRAIL_URL", "http://localhost:8004")
        ),
    ]
    
    for service in services:
        await service_registry.register_service(service)
    
    logger.info("Service integration gateway initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if redis_client:
        await redis_client.close()

# API Endpoints

class ServiceRequest(BaseModel):
    """Service request model."""
    service_name: str
    endpoint: str
    method: str = "POST"
    data: Optional[Dict] = None

class EventPublishRequest(BaseModel):
    """Event publish request."""
    event_type: str
    data: Dict[str, Any]

@app.get("/health")
async def health_check() -> Dict:
    """Gateway health check."""
    return {
        "status": "healthy",
        "service": "Service Integration Gateway",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/services/health")
async def get_services_health() -> Dict[str, ServiceHealth]:
    """Get health status of all services."""
    health = await service_registry.health_check_all()
    return {name: asdict(h) for name, h in health.items()}

@app.get("/services")
async def list_services() -> List[Dict]:
    """List all registered services."""
    services = await service_registry.list_services()
    return [asdict(s) for s in services]

@app.post("/request")
async def forward_request(request: ServiceRequest, background_tasks: BackgroundTasks) -> Any:
    """Forward request to service."""
    try:
        result = await event_orchestrator.forward_to_service(
            request.service_name,
            request.endpoint,
            request.method,
            request.data
        )
        
        # Log to audit trail
        background_tasks.add_task(
            event_orchestrator.publish_event,
            "service_request",
            {
                "service": request.service_name,
                "endpoint": request.endpoint,
                "method": request.method
            }
        )
        
        return result
    except Exception as e:
        logger.error(f"Request forwarding failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/events/publish")
async def publish_event(request: EventPublishRequest, background_tasks: BackgroundTasks) -> Dict:
    """Publish event across services."""
    await event_orchestrator.publish_event(request.event_type, request.data)
    return {"status": "published", "event_type": request.event_type}

@app.get("/status")
async def gateway_status() -> Dict:
    """Get gateway and services status."""
    health = await service_registry.health_check_all()
    healthy_count = sum(1 for h in health.values() if h.status == ServiceStatus.HEALTHY)
    
    return {
        "gateway": "healthy",
        "services_total": len(health),
        "services_healthy": healthy_count,
        "services": {name: asdict(h) for name, h in health.items()},
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
