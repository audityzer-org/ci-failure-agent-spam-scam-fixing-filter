# Scaling & Performance Optimization Guide
## Horizontal & Vertical Scaling for auditorsec.com & audityzer.com

---

## 1. Horizontal Pod Autoscaling (HPA)

### Configuration
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ci-failure-agent-hpa
  namespace: ci-failure-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ci-failure-agent
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 2
        periodSeconds: 30
      selectPolicy: Max
```

## 2. Vertical Pod Autoscaling (VPA)

### Install VPA
```bash
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/download/vertical-pod-autoscaler-0.12.0/vpa-v0.12.0.yaml
```

### VPA Recommendation Policy
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: ci-failure-agent-vpa
  namespace: ci-failure-agent
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind:       Deployment
    name:       ci-failure-agent
  updatePolicy:
    updateMode: "Auto"  # or "Off", "Initial", "Recreate"
```

## 3. Cluster Autoscaling

### Enable Cluster Autoscaler
```bash
# Terraform configuration
max_size = 10
min_size = 2
desired_capacity = 3

# Node scaling policies
auto_scaling_group {
  min_size         = 2
  max_size         = 10
  desired_capacity = 3
}
```

## 4. Performance Optimization

### Database Connection Pooling
```python
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Caching Strategy
```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_URL': REDIS_URL})

@app.route('/api/data')
@cache.cached(timeout=300)
def get_data():
    return expensive_operation()
```

### Response Compression
```bash
# Configure in Nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1000;
```

## 5. Load Balancing

### ALB Configuration
```bash
# Health check
path = "/health"
interval = 30
timeout = 5
healthy_threshold = 2
unhealthy_threshold = 3

# Sticky sessions
stickiness = {
  type            = "lb_cookie"
  enabled         = true
  duration        = 3600
}
```

## 6. Cost Optimization

### Spot Instances
```bash
# In Terraform
capacity_type = "SPOT"  # 70% cheaper

# Max price
spot_price = "0.05"  # $0.05/hour
```

### Reserved Instances
```bash
# 1-year commitment: 40% savings
# 3-year commitment: 60% savings
reservation_type = "RESERVED"
term = "THREE_YEARS"
```

## 7. Monitoring Scaling

### Metrics to Track
```promql
# Pod count
count(container_last_seen{pod=~"ci-failure-agent.*"})

# Node count
count(node_memory_MemTotal_bytes)

# Scaling events
rate(karpenter_nodes_allocatable_resources_total[5m])
```

## 8. Performance Benchmarks

### Target Metrics
- Latency: p95 < 200ms
- Throughput: > 1000 req/s
- CPU: < 70%
- Memory: < 80%
- Network: < 100 Mbps

---

**Version**: 1.0.0
