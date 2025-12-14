# Architecture & Design Decisions
## CI Failure Agent - Critical Configuration Document
**Date**: December 14, 2025 | **Status**: Pending Stakeholder Approval

---

## EXECUTIVE SUMMARY

This document addresses 5 critical architectural decisions that will define the system's scalability, reliability, and operational characteristics. Each decision has significant implications for development timeline, infrastructure costs, and feature capabilities.

---

## 1. PROCESSING MODEL: SYNC vs ASYNC/JOB-BASED

### DECISION REQUIRED: Analysis Processing Architecture

#### Option A: SYNCHRONOUS (Current Implementation)
**Architecture**:
```
Client → Request → FastAPI → Gemini API → Response (30-60 sec)
                  └─ Single connection held
```

**Pros**:
- ✅ Simple implementation
- ✅ Immediate feedback to client
- ✅ No database required initially
- ✅ Lower latency for small logs (<5KB)
- ✅ Easier debugging

**Cons**:
- ❌ Connection timeout risk (30+ sec logs)
- ❌ Client must wait for response
- ❌ Difficult to scale (limited concurrency)
- ❌ No audit trail of requests
- ❌ Failed requests lose context

**Best For**: Development, MVP, internal tools

---

#### Option B: ASYNC/JOB-BASED WITH WEBHOOKS (Recommended for Production)
**Architecture**:
```
Client → POST /analyze → Queue Job → Return Job ID (immediate)
                                ↓
                    Background Worker (async)
                                ↓
                       Gemini API (2-5 min)
                                ↓
                    POST to Webhook (client's URL)
```

**Pros**:
- ✅ Handles large logs (100MB+)
- ✅ Scalable to thousands of requests
- ✅ Natural retry/failure handling
- ✅ Audit trail of all requests
- ✅ Decouples client from analysis
- ✅ Better resource utilization

**Cons**:
- ❌ Requires message queue (RabbitMQ, Redis, AWS SQS)
- ❌ Requires database for job tracking
- ❌ Client must provide webhook URL
- ❌ More complex implementation (2-3 weeks)
- ❌ Requires monitoring/alerting

**Best For**: Production, SaaS, high-volume use

**Implementation Estimate**: 3-4 weeks (including queue, worker, webhooks)

**Recommended**: **HYBRID APPROACH**
- Sync mode for logs < 10KB (fast path)
- Async mode for logs > 10KB (slow path with webhooks)

---

## 2. MAXIMUM LOG SIZE LIMIT

### DECISION REQUIRED: Request Payload Limits

| Metric | Recommended | Range | Rationale |
|--------|-------------|-------|----------|
| **Per-Request Limit** | **50 MB** | 10MB - 500MB | Balance between use case and API limits |
| **Timeout Duration** | **5 minutes** | 30sec - 30min | Gemini API typical response time |
| **Concurrent Uploads** | **100 per IP** | 10 - 1000 | Prevent abuse while allowing scale |

### Cost Implications
50MB × 100 concurrent = 5GB temp storage needed

**Storage Options**:
1. **AWS S3** ($0.023/GB): $0.12/day for temp files
2. **Google Cloud Storage** ($0.020/GB): $0.10/day
3. **Local Disk** (on Render): Free but limited to ~10GB free tier

**Recommendation**: Use **50 MB limit** with S3 staging for large files

---

## 3. MULTI-TENANCY SUPPORT

### DECISION REQUIRED: Single vs Multi-Tenant Architecture

#### Option A: SINGLE-TENANT (Current)
**Architecture**: One API Key = Full Access

```python
# Current implementation
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# No tenant isolation
```

**Pros**:
- ✅ Simple implementation
- ✅ Fast to market
- ✅ Lower operational overhead

**Cons**:
- ❌ Cannot serve multiple organizations
- ❌ Cannot track usage per client
- ❌ Cannot implement per-tenant billing
- ❌ No data isolation

---

#### Option B: MULTI-TENANT (Recommended for Scale)
**Architecture**:
```
API Key → Organization ID → Data Isolation → Usage Tracking
            ↓
         tenant_id in JWT → Database row level security
```

**Implementation**:
```python
# Required additions
1. Add to database schema:
   - organizations table (id, name, api_key_hash, tier)
   - api_keys table (key_hash, organization_id, permissions)
   - audit_logs (tenant_id, action, timestamp, user_id)

2. Middleware for tenant isolation:
   @app.middleware("http")
   async def tenant_middleware(request, call_next):
       api_key = request.headers.get("X-API-Key")
       tenant = await get_tenant_from_key(api_key)
       request.state.tenant_id = tenant.id
       return await call_next(request)

3. Query filtering:
   SELECT * FROM analyses 
   WHERE tenant_id = request.state.tenant_id
```

**Pros**:
- ✅ Support multiple organizations
- ✅ Per-tenant usage tracking
- ✅ Per-tenant billing/quotas
- ✅ Data security/isolation
- ✅ API key rotation support

**Cons**:
- ❌ Requires database (3-4 weeks)
- ❌ More complex security
- ❌ Operational overhead

**Recommendation**: **Implement MULTI-TENANT from day 1**
- Minimal additional effort
- Essential for any B2B product
- Can start with 1 organization as test

**Implementation Estimate**: 2-3 weeks (with database)

---

## 4. RATE LIMITING & QUOTAS

### DECISION REQUIRED: Usage Limits per API Key

**Recommended Tiering**:

| Tier | Requests/Min | Requests/Month | Log Size | Cost |
|------|-------------|-----------------|----------|------|
| **Free** | 10 | 1,000 | 1 MB | $0 |
| **Starter** | 100 | 50,000 | 50 MB | $29/mo |
| **Pro** | 1,000 | 500,000 | 500 MB | $99/mo |
| **Enterprise** | Unlimited | Unlimited | 5 GB | Custom |

**Implementation Stack**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/analyze")
@limiter.limit("100/minute")  # 100 requests per minute
async def analyze_ci_failure(request: FailureAnalysisRequest):
    pass
```

**Database Tracking**:
```sql
CREATE TABLE api_usage (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES organizations(id),
    api_key_id UUID REFERENCES api_keys(id),
    request_count INT,
    bytes_processed INT,
    period_start TIMESTAMP,
    period_end TIMESTAMP
);
```

**Costs**:
- **Redis** for rate limiting: $0.50-2/month (Upstash)
- **Database** for tracking: Included with PostgreSQL
- **Monitoring**: $10-50/month (Datadog, New Relic)

**Recommendation**: **100 req/min per API key** (adjustable by tier)

---

## 5. DATABASE REQUIREMENTS FOR AUDIT TRAILS

### DECISION REQUIRED: Persistence Layer

#### Database Schema (REQUIRED for Production)

```sql
-- Core tables
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    created_at TIMESTAMP,
    subscription_tier VARCHAR(50),
    api_quota_monthly INT,
    storage_gb INT
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    key_hash VARCHAR(255) UNIQUE,
    last_used TIMESTAMP,
    created_at TIMESTAMP,
    permissions JSONB
);

-- Audit & Analysis
CREATE TABLE analyses (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES organizations(id),
    workflow_name VARCHAR(255),
    logs_size_bytes INT,
    status VARCHAR(50), -- pending, processing, completed, failed
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_duration_seconds INT,
    api_cost_usd NUMERIC
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES organizations(id),
    action VARCHAR(100),
    resource_type VARCHAR(50),
    resource_id UUID,
    changes JSONB,
    ip_address INET,
    user_agent VARCHAR(500),
    timestamp TIMESTAMP,
    INDEX (tenant_id, timestamp)
);

CREATE TABLE webhooks (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES organizations(id),
    url VARCHAR(500),
    events VARCHAR[] -- ['analysis.completed', 'analysis.failed']
    active BOOLEAN,
    secret_key VARCHAR(255),
    last_called TIMESTAMP,
    failure_count INT
);
```

#### Database Options:

| Option | Cost | Latency | Scalability | Setup |
|--------|------|---------|-------------|-------|
| **PostgreSQL (Neon)** | $10-50/mo | <10ms | Good | Easy |
| **MongoDB Atlas** | $10-100/mo | <10ms | Excellent | Easy |
| **DynamoDB** | $0-100+/mo | <20ms | Excellent | Medium |
| **Supabase** | $5-100/mo | <10ms | Good | Very Easy |

**Recommendation**: **Neon PostgreSQL** or **Supabase**
- PostgreSQL provides strong consistency
- Both offer free tier for dev/testing
- Easy migration to managed services
- Standard SQL for familiar tooling

**Setup Estimate**: 1 week (schema + migrations + ORM)

---

## IMPLEMENTATION PRIORITY MATRIX

```
HIGH PRIORITY (Week 1-2)
├─ Database schema & migrations
├─ API key authentication
├─ Tenant isolation middleware
└─ Audit logging

MEDIUM PRIORITY (Week 3-4)
├─ Rate limiting with Redis
├─ Usage tracking & quotas
├─ Webhook support
└─ Job queue (async mode)

LOW PRIORITY (Week 5+)
├─ Advanced analytics
├─ Billing integration
├─ Admin dashboard
└─ Custom webhooks filtering
```

---

## RECOMMENDED PRODUCTION STACK

**Processing**: Hybrid (sync + async)
**Log Size**: 50 MB max (S3 for larger)
**Multi-Tenancy**: ✅ Enabled
**Rate Limiting**: 100 req/min per API key
**Database**: PostgreSQL (Neon/Supabase)
**Queue**: Redis or Bull (for job processing)
**Storage**: S3 for large logs
**Monitoring**: Sentry + Datadog

**Total Development Time**: 6-8 weeks
**Total Monthly Cost**: $100-300 at scale

---

## DECISION CHECKLIST

Please confirm the following before implementation:

- [ ] **Processing Model**: Sync Only / Async Only / Hybrid?
- [ ] **Max Log Size**: 50MB / 100MB / Custom?
- [ ] **Multi-Tenancy**: Yes / No / Phase 2?
- [ ] **Rate Limit**: 100/min / 1000/min / Custom?
- [ ] **Database**: PostgreSQL / MongoDB / Other?
- [ ] **Deployment Target**: Render / AWS / GCP / Custom?
- [ ] **Timeline**: Aggressive (4 weeks) / Standard (8 weeks) / Flexible?
- [ ] **Budget**: Development cost priority?

---

## NEXT STEPS

1. **Stakeholder Review**: Present this document to team
2. **Decision Approval**: Confirm all 5 design decisions
3. **Architecture Review**: Technical team validates approach
4. **Sprint Planning**: Break into 2-week sprints
5. **Implementation**: Execute with clear milestones

**Estimated Complete Production Ready**: January 15, 2026
