# Phase 3.6: Performance Optimization & Benchmarking

## Summary

Phase 3.6 implements performance optimizations for the Orchestration Engine focused on async operations, caching strategies, and comprehensive benchmarking.

## Optimization Strategies

### 1. Async/Await Optimization

**Current State**: `process_alert()` and `_fetch_predictive_propositions_with_retry()` are already async.

**Recommended Enhancements**:

```python
# Add asyncio.gather for concurrent operations
async def process_multiple_alerts(alerts: List[Alert]) -> List[Dict]:
    """Process multiple alerts concurrently."""
    tasks = [self.process_alert(alert) for alert in alerts]
    return await asyncio.gather(*tasks, return_exceptions=True)

# Add asyncio.timeout for request timeouts  
async def _fetch_with_timeout(self, alert: Alert, timeout_sec: float):
    try:
        return await asyncio.wait_for(
            self._fetch_predictive_propositions(alert),
            timeout=timeout_sec
        )
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching propositions for {alert.id}")
        return []
```

### 2. Caching Strategy

**In-Memory Cache**:
- Cache proposition results for identical alert types (24-hour TTL)
- Cache user decision outcomes for similar alerts
- Implement LRU (Least Recently Used) eviction policy

```python
from functools import lru_cache
import time

class PropositionCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 86400):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.timestamps = {}
    
    def get(self, alert_type: str) -> Optional[List[PredictiveProposition]]:
        if alert_type not in self.cache:
            return None
        
        # Check TTL
        if time.time() - self.timestamps[alert_type] > self.ttl:
            del self.cache[alert_type]
            return None
        
        return self.cache[alert_type]
    
    def set(self, alert_type: str, propositions: List[PredictiveProposition]):
        # Implement LRU eviction
        if len(self.cache) >= self.max_size:
            oldest = min(self.timestamps, key=self.timestamps.get)
            del self.cache[oldest]
            del self.timestamps[oldest]
        
        self.cache[alert_type] = propositions
        self.timestamps[alert_type] = time.time()
```

**Redis Cache** (for distributed deployments):
- Use Redis for distributed caching across multiple instances
- Implement cache invalidation on proposition updates

### 3. Database Query Optimization

**Indexing Strategy**:
- Index on `alert_id` for fast lookups
- Index on `timestamp` for temporal queries
- Composite index on `(alert_type, timestamp)` for filtering

**Query Batching**:
```python
# Instead of individual queries
for alert_id in alert_ids:
    log = await db.get_proposition_log(alert_id)

# Use batch retrieval
logs = await db.get_proposition_logs_batch(alert_ids)
```

### 4. Connection Pooling

**HTTP Connection Pool**:
```python
# Already using httpx.AsyncClient with connection pooling
# Increase pool size for high concurrency
self.client = httpx.AsyncClient(
    timeout=30.0,
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)
```

### 5. Batch Processing

```python
# Process alerts in batches for better throughput
async def process_alert_batch(self, alerts: List[Alert], batch_size: int = 10):
    results = []
    for i in range(0, len(alerts), batch_size):
        batch = alerts[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[self.process_alert(alert) for alert in batch]
        )
        results.extend(batch_results)
    return results
```

## Benchmark Results (Target)

### Throughput
- **Single Alert**: < 200ms p99 latency
- **Batch (10 alerts)**: < 500ms p99 latency  
- **Concurrent (100 alerts)**: < 2s p99 latency

### Memory
- **Base**: ~50MB RSS
- **With 1000 cached propositions**: ~150MB RSS
- **Memory growth rate**: < 1MB per 100 requests

### Cache Hit Ratio
- **Target**: 60-70% for typical workloads
- **CI failures**: 75%+ (highly repetitive)
- **Scam incidents**: 40-50% (more varied)

## Performance Monitoring

```python
import time
from statistics import mean

class PerformanceMonitor:
    def __init__(self):
        self.latencies = []
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_latency(self, duration_ms: float):
        self.latencies.append(duration_ms)
    
    def get_percentile(self, p: float) -> float:
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * (p / 100))
        return sorted_latencies[index]
    
    def get_stats(self) -> Dict[str, float]:
        return {
            "p50": self.get_percentile(50),
            "p95": self.get_percentile(95),
            "p99": self.get_percentile(99),
            "avg": mean(self.latencies),
            "cache_hit_ratio": self.cache_hits / (self.cache_hits + self.cache_misses)
        }
```

## Implementation Roadmap

### Week 1: Async Optimization
- Add `process_multiple_alerts()` method
- Implement `asyncio.timeout` wrapper
- Test concurrent request handling

### Week 2: Caching
- Implement in-memory PropositionCache
- Add cache hit/miss tracking
- Set up Redis caching (optional)

### Week 3: Database Optimization
- Create indexes
- Implement batch queries
- Test query performance

### Week 4: Benchmarking
- Run load tests (100-1000 concurrent requests)
- Profile memory usage
- Measure cache hit ratios
- Document results

## Benchmarking Tools

```python
# Use k6 for load testing
import subprocess

script = """
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  vus: 100,      // 100 concurrent users
  duration: '60s' // 60 second test
};

export default function() {
  let response = http.post('http://localhost:8000/api/v1/alerts/process', {...});
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200
  });
}
"""

subprocess.run(['k6', 'run', '-'], input=script.encode())
```

## Expected Improvements

- **Latency**: 40-50% reduction with caching
- **Throughput**: 3-5x increase with async batching
- **Memory**: 20-30% reduction with better pooling
- **Cost**: 30-40% reduction in compute resources

## Monitoring Metrics

Track these metrics in production:
- Request latency (p50, p95, p99)
- Cache hit ratio
- Database query time
- HTTP connection pool utilization
- Memory usage trends
- Error rates by type

