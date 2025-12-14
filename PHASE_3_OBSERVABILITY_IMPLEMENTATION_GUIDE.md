# Phase 3 Implementation Guide: Advanced Observability Stack

## Overview
Phase 3 focuses on implementing a comprehensive observability stack with Prometheus, Grafana, and Loki for monitoring, alerting, and log aggregation.

**Timeline**: December 30, 2025 - January 3, 2026 (1 week)
**Status**: 📅 SCHEDULED
**Priority**: HIGH
**Dependencies**: Phase 1 (EKS cluster) and Phase 2 (DNS/TLS) must be complete

---

## Phase 3 Objectives

1. **Prometheus Installation** - Deploy metrics collection system
2. **Grafana Setup** - Create visualization dashboards
3. **Loki Deployment** - Configure log aggregation
4. **Custom Dashboards** - Build performance and health dashboards
5. **Alert Rules** - Set up automated alerting
6. **Performance Baseline** - Establish baseline metrics

---

## Step 1: Prometheus Installation

### 1.1 Install Prometheus via Helm

```bash
# Add Prometheus community Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values prometheus-values.yaml

# Verify installation
kubectl get pods -n monitoring
kubectl get svc -n monitoring
```

### 1.2 Prometheus Configuration

**File**: `prometheus-values.yaml`

```yaml
prometheus:
  prometheusSpec:
    retention: 15d
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
    
    scrapeInterval: 30s
    evaluationInterval: 30s
    
    serviceMonitorSelectorNilUsesHelmValues: false
    ruleNamespaceSelectorNilUsesHelmValues: false

grafana:
  enabled: true
  adminPassword: "YOUR_SECURE_PASSWORD"

alertmanager:
  enabled: true
  config:
    global:
      resolve_timeout: 5m
```

---

## Step 2: Grafana Dashboard Setup

### 2.1 Access Grafana

```bash
# Port forward to local machine
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Access at http://localhost:3000
# Default credentials: admin / YOUR_SECURE_PASSWORD
```

### 2.2 Create Custom Dashboards

**Dashboard 1**: Application Performance
- Request rate (requests/sec)
- Response time (p50, p95, p99)
- Error rate (%)
- Throughput (MB/sec)

**Dashboard 2**: Infrastructure Health
- CPU utilization per node
- Memory usage per pod
- Network I/O
- Disk usage

**Dashboard 3**: Kubernetes Cluster
- Pod status and distribution
- Node resource utilization
- PersistentVolume usage
- Namespace resource quotas

---

## Step 3: Loki Log Aggregation

### 3.1 Install Loki

```bash
# Add Grafana Helm repository
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Loki stack
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --values loki-values.yaml

# Verify installation
kubectl get pods -n monitoring | grep loki
```

### 3.2 Loki Configuration

**File**: `loki-values.yaml`

```yaml
loki:
  enabled: true
  persistence:
    enabled: true
    size: 100Gi
  
  config:
    limits_config:
      enforce_metric_name: false
      reject_old_samples: true
      reject_old_samples_max_age: 168h

promtail:
  enabled: true
  config:
    clients:
      - url: http://loki:3100/loki/api/v1/push

grafana:
  datasources:
    datasources.yaml:
      apiVersion: 1
      datasources:
        - name: Loki
          type: loki
          url: http://loki:3100
          access: proxy
```

---

## Step 4: Alert Rules Configuration

### 4.1 Define Alert Rules

**File**: `k8s/prometheus-alert-rules.yaml`

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ci-failure-agent-alerts
  namespace: monitoring
spec:
  groups:
    - name: ci-failure-agent
      interval: 30s
      rules:
        - alert: HighErrorRate
          expr: rate(http_requests_total{job="ci-failure-agent",status=~"5.."}[5m]) > 0.05
          for: 5m
          annotations:
            summary: "High error rate detected"
            description: "Error rate is {{ $value | humanizePercentage }} for 5 minutes"
        
        - alert: HighLatency
          expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 1
          for: 5m
          annotations:
            summary: "High latency detected"
            description: "P99 latency is {{ $value | humanizeDuration }}"
        
        - alert: PodCrashLooping
          expr: rate(kube_pod_container_status_restarts_total[30m]) > 0
          for: 5m
          annotations:
            summary: "Pod {{ $labels.pod }} is crash looping"
        
        - alert: HighMemoryUsage
          expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.9
          for: 5m
          annotations:
            summary: "High memory usage"
            description: "Memory usage is {{ $value | humanizePercentage }}"
```

```bash
# Apply alert rules
kubectl apply -f k8s/prometheus-alert-rules.yaml

# Verify rules
kubectl get prometheusrules -n monitoring
```

---

## Step 5: Performance Baseline

### 5.1 Establish Baseline Metrics

```bash
# Record initial metrics (run after stable operation for 1 hour)
kubectl exec -n monitoring prometheus-<pod-id> -- \
  promtool query instant \
    'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))'

# Baseline targets:
# - P99 Latency: < 200ms
# - Error Rate: < 0.1%
# - CPU Usage: < 70%
# - Memory Usage: < 80%
# - Disk Usage: < 85%
```

### 5.2 Dashboard Queries

```promql
# Request Rate
rate(http_requests_total[5m])

# Error Rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Response Time
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Pod Restart Count
kube_pod_container_status_restarts_total

# CPU Usage
rate(container_cpu_usage_seconds_total[5m])

# Memory Usage
container_memory_usage_bytes / container_spec_memory_limit_bytes
```

---

## Step 6: Verification & Testing

### 6.1 Health Checks

```bash
# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus-kube-prom-prometheus 9090:9090
# Visit http://localhost:9090/targets

# Check Grafana datasources
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Visit http://localhost:3000/datasources

# Check Loki logs
kubectl logs -n monitoring -l app=loki
```

### 6.2 Generate Test Load

```bash
# Install Apache Bench
apt-get install apache2-utils

# Generate requests
ab -n 1000 -c 100 https://ci-failure-agent.io/

# Monitor in Grafana
# Observe metrics updating in real-time
```

---

## Deliverables Checklist

- [ ] Prometheus installed and operational
- [ ] Grafana accessible and configured
- [ ] Loki installed for log aggregation
- [ ] Custom dashboards created (3+ dashboards)
- [ ] Alert rules configured and verified
- [ ] ServiceMonitors created for all services
- [ ] Prometheus targets scraping successfully
- [ ] Grafana datasources configured
- [ ] Performance baseline established
- [ ] Test load generated and monitored
- [ ] Documentation updated

---

## Next Steps

→ **Phase 4**: Helm Charts & GitOps Deployment (Starting Jan 6)

---

**Document Version**: 1.0
**Created**: December 14, 2025
**Owner**: Observability/SRE Team
