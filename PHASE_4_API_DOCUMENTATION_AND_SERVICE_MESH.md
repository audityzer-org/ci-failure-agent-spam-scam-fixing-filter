# Phase 4: API Documentation & Service Mesh

## Overview
Phase 4 focuses on documenting all APIs and implementing a service mesh infrastructure for better service-to-service communication, observability, and traffic management.

## Objectives
- Generate comprehensive OpenAPI 3.0 specifications
- Create interactive API documentation (Swagger UI, ReDoc)
- Implement Istio service mesh for traffic management
- Configure mutual TLS (mTLS) between services
- Set up service discovery and load balancing
- Implement circuit breakers and retry policies
- Enable distributed tracing integration

## API Documentation

### 1. OpenAPI Specification

**File Structure**:
```
api/
├── openapi.yaml              # Main OpenAPI 3.0 specification
├── schemas/
│   ├── workflow.yaml         # Workflow schemas
│   ├── state_machine.yaml    # State machine schemas
│   ├── task_queue.yaml       # Task queue schemas
│   └── errors.yaml           # Error response schemas
├── paths/
│   ├── workflows.yaml        # /workflows endpoints
│   ├── cases.yaml            # /cases endpoints
│   ├── tasks.yaml            # /tasks endpoints
│   └── health.yaml           # /health endpoints
└── examples/
    ├── workflow_requests.yaml
    ├── case_requests.yaml
    └── task_requests.yaml
```

### 2. API Endpoints

#### Workflow Management API
```yaml
GET /api/v1/workflows
  - Description: List all workflows
  - Parameters:
    - status: filter by workflow status
    - limit: pagination limit (default: 100)
    - offset: pagination offset (default: 0)
  - Response: 200 - List of workflows

POST /api/v1/workflows
  - Description: Create new workflow
  - Request Body: WorkflowDefinition
  - Response: 201 - Created workflow

GET /api/v1/workflows/{workflowId}
  - Description: Get workflow details
  - Response: 200 - Workflow details

PUT /api/v1/workflows/{workflowId}
  - Description: Update workflow
  - Request Body: WorkflowUpdate
  - Response: 200 - Updated workflow

DELETE /api/v1/workflows/{workflowId}
  - Description: Delete workflow
  - Response: 204 - No content
```

#### Case Management API
```yaml
GET /api/v1/cases
  - Description: List all cases
  - Parameters:
    - state: filter by case state
    - priority: filter by priority
    - limit, offset: pagination
  - Response: 200 - List of cases

POST /api/v1/cases
  - Description: Create new case
  - Request Body: CaseDefinition
  - Response: 201 - Created case

GET /api/v1/cases/{caseId}
  - Description: Get case details with state history
  - Response: 200 - Case details

PUT /api/v1/cases/{caseId}/state
  - Description: Update case state
  - Request Body: StateTransitionRequest
  - Response: 200 - Updated case
```

#### Task Queue API
```yaml
GET /api/v1/tasks
  - Description: List tasks by queue
  - Parameters:
    - queue: queue name (required)
    - status: filter by status
    - limit, offset: pagination
  - Response: 200 - List of tasks

POST /api/v1/tasks
  - Description: Enqueue new task
  - Request Body: TaskDefinition
  - Response: 201 - Created task

GET /api/v1/tasks/{taskId}
  - Description: Get task details
  - Response: 200 - Task details

PATCH /api/v1/tasks/{taskId}
  - Description: Update task status
  - Request Body: TaskStatusUpdate
  - Response: 200 - Updated task
```

#### Health & Status API
```yaml
GET /health
  - Description: Basic health check
  - Response: 200 - {"status": "healthy"}

GET /health/live
  - Description: Liveness probe for Kubernetes
  - Response: 200 - Service is running

GET /health/ready
  - Description: Readiness probe for Kubernetes
  - Response: 200/503 - Service ready for traffic

GET /metrics
  - Description: Prometheus metrics
  - Response: 200 - Prometheus format metrics
```

### 3. API Documentation Tools

#### Swagger UI
- **Path**: `/api/docs`
- **Configuration**: FastAPI built-in Swagger UI
- **Features**:
  - Interactive API exploration
  - Request/response examples
  - Authentication testing
  - Schema visualization

#### ReDoc
- **Path**: `/api/redoc`
- **Features**:
  - Beautiful documentation layout
  - Mobile-friendly
  - Schema references
  - Examples and use cases

#### OpenAPI JSON Schema
- **Path**: `/openapi.json`
- **Format**: OpenAPI 3.0.0
- **Usage**: IDE integration, client generation

## Service Mesh Implementation (Istio)

### 1. Istio Installation

```bash
# Install Istio in Kubernetes cluster
istioctlInstall --set profile=demo

# Enable sidecar injection for namespace
kubectl label namespace default istio-injection=enabled
```

### 2. VirtualService Configuration

```yaml
# services/virtual-service.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: workflow-orchestrator
spec:
  hosts:
  - workflow-orchestrator
  http:
  - match:
    - uri:
        prefix: /api/v1/workflows
    route:
    - destination:
        host: workflow-orchestrator
        port:
          number: 8000
      weight: 100
    timeout: 30s
    retries:
      attempts: 3
      perTryTimeout: 10s
```

### 3. DestinationRule Configuration

```yaml
# services/destination-rule.yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: workflow-orchestrator
spec:
  host: workflow-orchestrator
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 100
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      splitExternalLocalOriginErrors: true
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

### 4. Gateway Configuration

```yaml
# services/gateway.yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: api-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "api.example.com"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: api-cert
    hosts:
    - "api.example.com"
```

### 5. Mutual TLS (mTLS)

```yaml
# services/peer-authentication.yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT  # Enforce mTLS for all traffic
```

```yaml
# services/request-authentication.yaml
apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
```

### 6. Traffic Management Policies

#### Circuit Breaker
```yaml
# services/circuit-breaker.yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: api-circuit-breaker
spec:
  host: api-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minRequestVolume: 10
```

#### Rate Limiting
```yaml
# services/rate-limit.yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: ratelimit
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
```

### 7. Canary Deployments

```yaml
# services/canary-deployment.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: workflow-orchestrator-canary
spec:
  hosts:
  - workflow-orchestrator
  http:
  - match:
    - uri:
        prefix: /api/v1
    route:
    - destination:
        host: workflow-orchestrator
        subset: v1
      weight: 90
    - destination:
        host: workflow-orchestrator
        subset: v2
      weight: 10
```

## Service Discovery

### Kubernetes Service Configuration
```yaml
apiVersion: v1
kind: Service
metadata:
  name: workflow-orchestrator
spec:
  selector:
    app: workflow-orchestrator
  ports:
  - name: http
    port: 8000
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
  type: ClusterIP
```

## API Versioning Strategy

### Version 1 (Current)
- Base URL: `/api/v1`
- Supports: Workflows, Cases, Tasks, Health
- Deprecation: 2026-12-31

### Version 2 (Planned)
- Base URL: `/api/v2`
- New Features: Advanced filtering, batch operations
- Migration Window: 6 months overlap with v1

## Authentication & Authorization

### API Key Authentication
```python
from fastapi import Depends, Header

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403)
    return x_api_key
```

### JWT Authentication
```python
from fastapi_jwt import JwtAuthorizationCredentials, JwtBearer

security = JwtBearer()

@app.post("/protected")
async def protected_route(
    credentials: JwtAuthorizationCredentials = Depends(security)
):
    return {"token": credentials.token}
```

## API Documentation Generation

### FastAPI Auto-documentation
```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="CI Failure Agent",
    description="API for spam and scam detection",
    version="1.0.0"
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="CI Failure Agent API",
        version="1.0.0",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## Testing API Documentation

```bash
# Validate OpenAPI schema
spectacle lint openapi.yaml

# Generate client SDKs
openapi-generator generate -i openapi.yaml -g python-client -o ./client

# Test API endpoints
pytest tests/api/ -v
```

## Monitoring & Observability

### Istio Telemetry
- **Metrics**: Service latency, error rates, traffic volumes
- **Traces**: Distributed tracing with Jaeger
- **Logs**: Access logs, error logs

### Prometheus Integration
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: api-service
spec:
  selector:
    matchLabels:
      app: api-service
  endpoints:
  - port: metrics
    interval: 30s
```

## Next Steps
1. Generate OpenAPI 3.0 specification
2. Set up Swagger UI and ReDoc
3. Configure FastAPI application
4. Install and configure Istio
5. Create VirtualService and DestinationRule
6. Implement mTLS and authorization
7. Test API endpoints and service mesh
8. Proceed to Phase 5: Distributed Tracing & Monitoring
