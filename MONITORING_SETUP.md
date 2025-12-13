# Monitoring & Alerting Setup Guide

## Overview
This guide provides comprehensive monitoring and alerting setup for the CI Failure Agent production environment using industry-standard tools: Prometheus for metrics, Grafana for visualization, and AlertManager for alerts.

## Architecture

### Prometheus
- **Time-Series Database**: Stores all metrics with timestamps
- **Scrape Interval**: 15 seconds (configurable)
- **Retention**: 30 days (configurable)
- **Storage**: ~1.3GB per million samples

### Grafana
- **Visualization Platform**: Real-time dashboards
- **Data Source**: Prometheus
- **Authentication**: OAuth2 / LDAP / Local users
- **Alerting**: Via AlertManager

### AlertManager
- **Alert Router**: Manages alerts from Prometheus
- **Notifications**: Slack, PagerDuty, Email, Webhook
- **Grouping**: Reduces alert fatigue

## Installation

### 1. Prometheus Installation

```bash
# Using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --create-namespace \
  -f prometheus-values.yaml
```

### 2. Prometheus Configuration

```yaml
# prometheus-values.yaml
prometheus:
  prometheusSpec:
    retention: 30d
    scrapeInterval: 15s
    evaluationInterval: 15s
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 2000m
        memory: 4Gi
    
    # Service Monitors
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
```

### 3. Grafana Installation

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install grafana grafana/grafana \
  -n monitoring \
  -f grafana-values.yaml
```

### 4. Grafana Configuration

```yaml
# grafana-values.yaml
grafana:
  admin:
    existingSecret: grafana-admin
  datasources:
    datasources.yaml:
      apiVersion: 1
      datasources:
      - name: Prometheus
        type: prometheus
        url: http://prometheus-operated:9090
        access: proxy
        isDefault: true
```

## Key Metrics to Monitor

### Application Metrics
1. **Request Rate**: `rate(http_requests_total[5m])`
2. **Response Latency**: `histogram_quantile(0.99, http_request_duration_seconds)`
3. **Error Rate**: `rate(http_requests_total{status=~"5.."}[5m])`
4. **Active Requests**: `http_requests_in_progress`

### System Metrics
1. **CPU Usage**: `rate(container_cpu_usage_seconds_total[5m]) * 100`
2. **Memory Usage**: `container_memory_usage_bytes / 1024 / 1024`
3. **Disk Usage**: `node_filesystem_avail_bytes / node_filesystem_size_bytes`
4. **Network I/O**: `rate(container_network_transmit_bytes_total[5m])`

### Kubernetes Metrics
1. **Pod Restarts**: `increase(kube_pod_container_status_restarts_total[1h])`
2. **Node Status**: `kube_node_status_condition`
3. **PVC Usage**: `kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes`
4. **Deployment Replicas**: `kube_deployment_status_replicas_available`

### Database Metrics
1. **Query Latency**: `pg_stat_statements_mean_exec_time`
2. **Connection Pool**: `pg_stat_activity`
3. **Cache Hit Ratio**: `(blks_hit) / (blks_hit + blks_read)`
4. **Transaction Rate**: `rate(pg_stat_xact_tuples_inserted_total[5m])`

## Alert Rules

### Critical Alerts

```yaml
# prometheus-rules.yaml
groups:
- name: critical
  interval: 30s
  rules:
  - alert: HighErrorRate
    expr: |
      (rate(http_requests_total{status=~"5.."}[5m]) / 
       rate(http_requests_total[5m])) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }}"

  - alert: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total[1h]) > 5
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Pod {{ $labels.pod }} is crash looping"

  - alert: DiskSpaceRunningOut
    expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Disk space < 10% on {{ $labels.device }}"
```

### Warning Alerts

```yaml
  - alert: HighMemoryUsage
    expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.8
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Memory usage > 80% on {{ $labels.pod }}"

  - alert: HighCPUUsage
    expr: (rate(container_cpu_usage_seconds_total[5m]) * 100) > 80
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "CPU usage > 80% on {{ $labels.pod }}"

  - alert: SlowDatabaseQueries
    expr: pg_stat_statements_mean_exec_time > 1000
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Slow database queries detected"
```

## Dashboard Templates

### System Health Dashboard
- CPU, Memory, Disk usage over time
- Network I/O graphs
- System load averages
- Top consuming processes

### Application Performance Dashboard
- Request rate (RPS)
- Response time (p50, p95, p99)
- Error rate and error distribution
- Active connections
- Top slowest endpoints

### Kubernetes Cluster Dashboard
- Node status and capacity
- Pod distribution
- Resource requests vs actual usage
- Persistent volume utilization
- Network policies visualization

### Database Performance Dashboard
- Query execution time
- Connections and connection pool
- Replication lag
- Cache hit ratio
- Transaction rates
- Slow queries list

## Alerting Channels

### Slack Integration

```yaml
# alertmanager-config.yaml
route:
  receiver: 'slack-notifications'
  routes:
  - match:
      severity: critical
    receiver: 'critical-slack'
    continue: true
  - match:
      severity: warning
    receiver: 'warning-slack'

receivers:
- name: 'slack-notifications'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    channel: '#alerts'
    title: 'Alert: {{ .GroupLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

- name: 'critical-slack'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    channel: '#critical-alerts'
    title: 'CRITICAL: {{ .GroupLabels.alertname }}'
```

### PagerDuty Integration

```yaml
- name: 'pagerduty-notifications'
  pagerduty_configs:
  - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
    severity: '{{ if eq .Status "firing" }}critical{{ else }}error{{ end }}'
```

### Email Notifications

```yaml
- name: 'email-notifications'
  email_configs:
  - to: 'devops@company.com'
    from: 'alerts@company.com'
    smarthost: 'smtp.gmail.com:587'
    auth_username: 'alerts@company.com'
    auth_password: 'app-password'
    headers:
      Subject: 'Alert: {{ .GroupLabels.alertname }}'
```

## Maintenance & Optimization

### 1. Prometheus Maintenance

```bash
# Check storage usage
df -h /prometheus

# Compact WAL
curl -X POST http://localhost:9090/-/reload

# Backup Prometheus data
tar -czf prometheus-backup-$(date +%Y%m%d).tar.gz /prometheus
```

### 2. Grafana Maintenance

```bash
# Export dashboard
curl -H "Authorization: Bearer $GRAFANA_TOKEN" \
  http://localhost:3000/api/dashboards/db/my-dashboard | jq > dashboard.json

# Import dashboard
curl -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```

### 3. Metric Retention Optimization

```yaml
# Adjust retention based on storage
prometheus:
  prometheusSpec:
    retention: 14d  # Reduce from 30d to save storage
    walCompression: true  # Enable WAL compression
```

## Best Practices

1. **Alert Fatigue Reduction**
   - Set appropriate thresholds
   - Use alert grouping
   - Implement silencing for known issues
   - Use high confidence metrics only

2. **Metric Naming**
   - Use consistent naming conventions
   - Follow Prometheus naming standards
   - Document all custom metrics
   - Use labels for dimensionality

3. **Dashboard Design**
   - Focus on actionable metrics
   - Use appropriate time ranges
   - Include runbook links
   - Version control dashboards

4. **Alerting Strategy**
   - Alert on symptoms, not causes
   - Provide context in alert messages
   - Include remediation steps
   - Test alerts regularly

## Troubleshooting

### Alerts Not Firing
1. Check Prometheus status: `http://localhost:9090/status`
2. Verify alert rules: `http://localhost:9090/alerts`
3. Check AlertManager: `http://localhost:9093`
4. Review logs: `kubectl logs -f deployment/alertmanager -n monitoring`

### High Memory/CPU Usage
1. Reduce metric cardinality
2. Increase retention period cleanup
3. Optimize scrape intervals
4. Disable unused metrics

### Data Loss
1. Enable WAL persistence
2. Configure external storage (S3/GCS)
3. Implement regular backups
4. Use long-term storage solution

## References

- Prometheus Documentation: https://prometheus.io/docs
- Grafana Documentation: https://grafana.com/docs
- AlertManager Documentation: https://prometheus.io/docs/alerting/latest/overview
- Prometheus Query Language: https://prometheus.io/docs/prometheus/latest/querying/basics

---

**Document Version**: 1.0
**Last Updated**: 2024
**Maintained By**: Platform Team
**Review Frequency**: Quarterly
