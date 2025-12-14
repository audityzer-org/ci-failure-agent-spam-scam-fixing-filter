# Scaling Procedures Guide

## Overview
This guide provides comprehensive procedures for scaling the agentic AI system horizontally and vertically to handle increased load in production environments.

## 1. Vertical Scaling (Scale-Up)

### 1.1 Node/Pod Resource Increase
```yaml
# Update Kubernetes deployment resources
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ci-failure-agent
spec:
  template:
    spec:
      containers:
      - name: app
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### 1.2 Database Scaling
- Increase instance size (t3.medium → t3.large)
- Upgrade storage capacity
- Configure enhanced monitoring during upgrade
- Plan maintenance window for zero-downtime migration

### 1.3 Cache Layer Scaling
```bash
# Redis memory upgrade
redis-cli CONFIG GET maxmemory
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG REWRITE
```

## 2. Horizontal Scaling (Scale-Out)

### 2.1 Kubernetes Horizontal Pod Autoscaling (HPA)

#### Metrics-Based Scaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ci-failure-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ci-failure-agent
  minReplicas: 3
  maxReplicas: 20
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
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
      - type: Percent
        value: 50
        periodSeconds: 30
      - type: Pods
        value: 2
        periodSeconds: 30
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 25
        periodSeconds: 60
```

#### Custom Metrics Scaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ci-failure-agent-custom
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ci-failure-agent
  minReplicas: 2
  maxReplicas: 15
  metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
  - type: Pods
    pods:
      metric:
        name: queue_depth
      target:
        type: AverageValue
        averageValue: "10"
```

### 2.2 Manual Scaling Commands
```bash
# Scale deployment to specific number of replicas
kubectl scale deployment ci-failure-agent --replicas=5

# Monitor scaling progress
kubectl get hpa ci-failure-agent-hpa --watch

# Check pod distribution across nodes
kubectl get pods -o wide

# View scaling events
kubectl describe hpa ci-failure-agent-hpa
```

## 3. Database Scaling

### 3.1 Read Replicas

#### Aurora MySQL Configuration
```yaml
# RDS Aurora Auto-scaling policy
DBClusterIdentifier: ci-failure-agents-cluster
AutoMinorVersionUpgrade: true
BackupRetentionPeriod: 30
EnableMultiAZ: true
EnableIAMDatabaseAuthentication: true
EngineVersion: 8.0.28
StorageEncrypted: true
```

#### Adding Read Replicas
```sql
-- Create read replica in same AZ
CREATE DATABASE REPLICA FOR CLUSTER 'source-cluster'
MODE = READ_ONLY
REGION = current-region;

-- Create read replica in different AZ
CREATE DATABASE REPLICA FOR CLUSTER 'source-cluster'
MODE = READ_ONLY
REGION = 'us-east-2';
```

### 3.2 Connection Pooling Optimization
```python
# PgBouncer configuration for PostgreSQL
[databases]
ci_failures = host=primary.db.internal port=5432 dbname=ci_failures

[pgbouncer]
pool_mode = transaction
max_client_conn = 10000
default_pool_size = 25
min_pool_size = 10
reserve_pool_size = 5
reserve_pool_timeout = 3
```

### 3.3 Sharding Strategy

#### Hash-Based Sharding
```python
def get_shard_key(failure_id: str) -> int:
    """Determine shard based on failure ID"""
    num_shards = 8
    hash_value = hash(failure_id)
    return hash_value % num_shards

# Database connection
shard_id = get_shard_key(failure_id)
db = get_connection(f"shard_{shard_id}")
```

## 4. Load Balancing

### 4.1 Kubernetes Service Load Balancing
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ci-failure-agent-lb
spec:
  type: LoadBalancer
  selector:
    app: ci-failure-agent
  ports:
  - name: http
    port: 80
    targetPort: 8000
    protocol: TCP
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 3600
  loadBalancerSourceRanges:
  - 0.0.0.0/0
```

### 4.2 Ingress Configuration
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ci-failure-agent-ingress
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /api/failures
        pathType: Prefix
        backend:
          service:
            name: ci-failure-agent
            port:
              number: 8000
```

## 5. Caching Strategy for Scaling

### 5.1 Distributed Caching
```python
# Redis Cluster configuration
from redis.cluster import RedisCluster

redis_cluster = RedisCluster(
    startup_nodes=[
        {"host": "node1", "port": 6379},
        {"host": "node2", "port": 6379},
        {"host": "node3", "port": 6379}
    ],
    decode_responses=True,
    skip_full_coverage_check=True
)

# Cache with TTL
redis_cluster.setex(f"failure:{id}", 3600, json.dumps(failure_data))
```

### 5.2 Memcached for Session Scaling
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: memcached-config
data:
  memcached.conf: |
    -m 2048
    -p 11211
    -u memcache
    -c 10240
    -t 4
```

## 6. Message Queue Scaling

### 6.1 Kafka Configuration for Scaling
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: ci-failures-kafka
spec:
  kafka:
    version: 3.5.0
    replicas: 3
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"
      limits:
        memory: "2Gi"
        cpu: "1000m"
    config:
      num.partitions: 10
      default.replication.factor: 3
      min.insync.replicas: 2
      log.retention.hours: 168
      log.segment.bytes: 1073741824
```

### 6.2 Consumer Group Scaling
```python
from kafka import KafkaConsumer
from multiprocessing import Process

def consume_failures(group_id: str, partition_offset: int):
    consumer = KafkaConsumer(
        'ci-failures',
        group_id=group_id,
        bootstrap_servers=['localhost:9092'],
        max_poll_records=500,
        auto_offset_reset='earliest'
    )
    
    for message in consumer:
        process_failure(message.value)

# Start multiple consumer processes
for i in range(4):  # 4 consumer instances
    p = Process(target=consume_failures, args=(f'group-{i}', i))
    p.start()
```

## 7. Monitoring During Scaling

### 7.1 Key Metrics to Monitor
```yaml
scaling_metrics:
  - name: pod_cpu_utilization
    threshold: 80%
    action: scale_up
  - name: pod_memory_utilization
    threshold: 85%
    action: scale_up
  - name: response_latency_p99
    threshold: 500ms
    action: scale_up
  - name: database_connections
    threshold: 80%_of_max
    action: add_read_replicas
  - name: queue_depth
    threshold: 1000_messages
    action: increase_consumer_instances
```

### 7.2 Prometheus Alerting Rules
```yaml
groups:
- name: scaling.rules
  rules:
  - alert: HighPodCPU
    expr: avg(rate(container_cpu_usage_seconds_total[5m])) by (pod_name) > 0.8
    for: 5m
    annotations:
      summary: "Pod {{ $labels.pod_name }} CPU > 80%"
  
  - alert: HighMemoryUsage
    expr: container_memory_usage_bytes / 1024 / 1024 > 900
    for: 5m
    annotations:
      summary: "Pod memory usage > 900MB"
```

## 8. Cost Optimization During Scaling

### 8.1 Resource Right-Sizing
```bash
# Analyze actual resource usage
kubectl top pods -n default

# Check node utilization
kubectl top nodes

# Review resource requests vs actual usage
kubectl get pods -o json | jq '.items[] | {name: .metadata.name, cpu: .spec.containers[].resources.requests.cpu, memory: .spec.containers[].resources.requests.memory}'
```

### 8.2 Spot Instances for Cost Reduction
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ci-failure-agent-spot
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: karpenter.sh/capacity-type
                operator: In
                values: ["spot"]
      containers:
      - name: app
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
```

## 9. Scaling Runbook

### 9.1 Pre-Scaling Checklist
- [ ] Review current metrics and forecast demand
- [ ] Ensure database connections have headroom
- [ ] Verify load balancer capacity
- [ ] Check available cluster nodes/resources
- [ ] Plan maintenance window if needed
- [ ] Notify operations team
- [ ] Prepare rollback plan

### 9.2 Scaling Execution Steps
1. Monitor baseline metrics for 5 minutes
2. Initiate horizontal pod scaling
3. Wait for pods to reach Ready state
4. Verify traffic distribution across new pods
5. Monitor error rates and latency
6. If issues detected, trigger rollback
7. Update monitoring thresholds
8. Document actual vs. expected scaling behavior

### 9.3 Post-Scaling Validation
- [ ] All pods passing health checks
- [ ] Request latency within SLA
- [ ] Error rate < 0.1%
- [ ] Database query performance normal
- [ ] Cache hit ratio > 80%
- [ ] No unusual memory spikes

## 10. Disaster Recovery for Scaling

### 10.1 Scale-Down Procedure
```bash
# Graceful pod termination with drain
kubectl drain <node-name> --ignore-daemonsets --grace-period=600

# Scale deployment down
kubectl scale deployment ci-failure-agent --replicas=3

# Verify pods are rescheduled
kubectl get pods -o wide
```

### 10.2 Rollback Scaling Changes
```bash
# Rollback to previous deployment
kubectl rollout undo deployment/ci-failure-agent

# Verify rollback completed
kubectl rollout status deployment/ci-failure-agent

# Monitor metrics post-rollback
kubectl top pods
```

---

**Last Updated**: Generated automatically
**Version**: 1.0
**Status**: Production Ready
