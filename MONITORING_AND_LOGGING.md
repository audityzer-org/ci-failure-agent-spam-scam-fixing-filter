# Monitoring, Logging & Observability Guide
## Complete Observability Stack for auditorsec.com & audityzer.com

---

## Architecture Overview

### Stack Components:
1. **Prometheus** - Metrics collection & storage
2. **Grafana** - Visualization & dashboards
3. **Loki** - Log aggregation
4. **CloudWatch** - AWS native monitoring
5. **Alertmanager** - Alert routing & management

## 1. Prometheus Setup

### Install Prometheus via Helm
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace
```

### Scrape Configuration
```yaml
scrape_configs:
  - job_name: 'ci-failure-agent'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - ci-failure-agent
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
```

## 2. Grafana Dashboards

### Access Grafana
```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# http://localhost:3000 (admin/prom-operator)
```

### Key Metrics
- HTTP request rate
- Response time (p50, p95, p99)
- Error rates
- CPU/Memory usage
- Disk I/O
- Network metrics

## 3. Loki for Log Aggregation

### Install Loki Stack
```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack -n logging --create-namespace
```

### Log Queries
```logql
# Recent errors
{job="ci-failure-agent"} |= `ERROR`

# Request latency
{job="ci-failure-agent"} | json | duration > 1s

# Rate of errors
sum(rate({job="ci-failure-agent"} |= `ERROR` [5m]))
```

## 4. CloudWatch Integration

### Send Logs to CloudWatch
```bash
# Install Fluent Bit
helm repo add aws https://aws.github.io/eks-charts
helm install aws-for-fluent-bit aws/aws-for-fluent-bit \
  -n amazon-cloudwatch-observability
```

### View Logs
```bash
aws logs tail /aws/eks/ci-failure-agent-cluster/application --follow
```

## 5. Alerting

### Alert Rules
```yaml
groups:
  - name: application-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[1h]) > 5
        annotations:
          summary: "Pod is crash looping"
```

## 6. Custom Metrics

### Application Metrics (Python)
```python
from prometheus_client import Counter, Histogram, Gauge

request_count = Counter('app_requests_total', 'Total requests')
request_duration = Histogram('app_request_duration_seconds', 'Request duration')
active_users = Gauge('app_active_users', 'Active users')

@app.route('/api/endpoint')
def endpoint():
    with request_duration.time():
        request_count.inc()
        # endpoint logic
```

## 7. Performance Monitoring

### Key Metrics to Track
- **Availability**: 99.9%+ uptime
- **Latency**: p95 < 200ms
- **Error Rate**: < 0.1%
- **Throughput**: > 1000 req/s
- **Resource Usage**: < 80% CPU/Memory

### SLO Definition
```
Service: CI Failure Agent
Availability SLO: 99.95%
Latency SLO: 200ms p95
Error Rate SLO: 0.1%
```

## 8. Troubleshooting

### High CPU
```promql
top10(container_cpu_usage_seconds_total{pod=~"ci-failure-agent.*"})
```

### Memory Leaks
```promql
sum(container_memory_usage_bytes{pod=~"ci-failure-agent.*"}) by (pod)
```

### Pod Failures
```bash
kubectl get events -n ci-failure-agent
kubectl describe pod <pod-name> -n ci-failure-agent
```

---

**Version**: 1.0.0
