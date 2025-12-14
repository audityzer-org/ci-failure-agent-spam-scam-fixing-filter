# Phase 5: Distributed Tracing & Monitoring Dashboard

## Overview
Phase 5 implements comprehensive distributed tracing infrastructure using Jaeger and a centralized monitoring dashboard for real-time observability across all microservices.

## Objectives
- Implement distributed tracing with OpenTelemetry and Jaeger
- Create comprehensive Grafana dashboards
- Set up alerting rules and notification channels
- Configure centralized logging with ELK stack
- Implement application performance monitoring (APM)
- Create custom metrics and KPIs
- Establish operational runbooks

## Distributed Tracing Architecture

### 1. OpenTelemetry Implementation

**Dependencies**:
```python
# requirements.txt
opentelemetry-api==1.20.0
opentelemetry-sdk==1.20.0
opentelemetry-exporter-jaeger-thrift==1.20.0
opentelemetry-instrumentation==0.41b0
opentelemetry-instrumentation-fastapi==0.41b0
opentelemetry-instrumentation-requests==0.41b0
opentelemetry-instrumentation-sqlalchemy==0.41b0
opentelemetry-instrumentation-redis==0.41b0
```

**Configuration**:
```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# Jaeger Exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-agent",
    agent_port=6831,
)

# Tracer Provider
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)
trace.set_tracer_provider(tracer_provider)

# Instrumentation
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()
SQLAlchemyInstrumentor().instrument(
    engine=db_engine
)
```

### 2. Jaeger Deployment

**Kubernetes Deployment**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
    spec:
      containers:
      - name: jaeger
        image: jaegertracing/all-in-one:latest
        ports:
        - containerPort: 6831
          protocol: UDP
        - containerPort: 16686
          protocol: TCP
        environment:
        - name: COLLECTOR_ZIPKIN_HTTP_PORT
          value: "9411"
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger
spec:
  selector:
    app: jaeger
  ports:
  - name: jaeger-agent-zipkin-thrift
    port: 6831
    protocol: UDP
  - name: jaeger-collector-http
    port: 14268
    protocol: TCP
  - name: jaeger-ui
    port: 16686
    protocol: TCP
  type: ClusterIP
```

## Monitoring Dashboard

### 1. Prometheus Metrics

**Application Metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0)
)

# Workflow metrics
workflow_duration = Histogram(
    'workflow_execution_duration_seconds',
    'Workflow execution time',
    ['workflow_name', 'status']
)

workflow_steps_total = Counter(
    'workflow_steps_total',
    'Total workflow steps executed',
    ['workflow_name', 'step_name', 'status']
)

# Task queue metrics
queue_size = Gauge(
    'task_queue_size',
    'Number of tasks in queue',
    ['queue_name']
)

queue_processing_time = Histogram(
    'task_processing_duration_seconds',
    'Task processing duration',
    ['queue_name', 'status']
)
```

### 2. Grafana Dashboards

**Dashboard: System Overview**
- CPU and Memory usage
- Network I/O
- Disk usage
- Request rate and latency
- Error rate and 95th percentile latency

**Dashboard: Microservices Performance**
- Request duration by service
- Error rates by service
- Service dependency graph
- Traffic heatmap

**Dashboard: Business Metrics**
- Cases processed per hour
- Average case resolution time
- State transition rates
- Task queue throughput

**Dashboard: Infrastructure**
- Pod resource usage
- Node status and capacity
- PVC usage
- Network bandwidth

### 3. Grafana Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
data:
  prometheus.yaml: |
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus:9090
      isDefault: true
      access: proxy
    - name: Jaeger
      type: jaeger
      url: http://jaeger:16686
      access: proxy
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        volumeMounts:
        - name: datasources
          mountPath: /etc/grafana/provisioning/datasources
      volumes:
      - name: datasources
        configMap:
          name: grafana-datasources
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000
  type: LoadBalancer
```

## Alerting Strategy

### 1. Alert Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: application-alerts
spec:
  groups:
  - name: microservices.rules
    interval: 30s
    rules:
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
      for: 5m
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value }}%"
    
    - alert: HighLatency
      expr: histogram_quantile(0.95, http_request_duration_seconds) > 1.0
      for: 5m
      annotations:
        summary: "High request latency"
        description: "p95 latency is {{ $value }}s"
    
    - alert: WorkflowFailureRate
      expr: rate(workflow_steps_total{status="failed"}[5m]) > 0.1
      for: 10m
      annotations:
        summary: "High workflow failure rate"
    
    - alert: ServiceDown
      expr: up{job="kubernetes-pods"} == 0
      for: 2m
      annotations:
        summary: "Service {{ $labels.pod }} is down"
```

### 2. Notification Channels

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: alert-channels
type: Opaque
stringData:
  slack-webhook: "https://hooks.slack.com/services/YOUR/WEBHOOK"
  pagerduty-key: "YOUR_PAGERDUTY_KEY"
  email-config: "smtp://alerts@example.com"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
    route:
      receiver: 'default'
      group_by: ['alertname', 'cluster']
      routes:
      - match:
          severity: critical
        receiver: 'pagerduty'
        continue: true
      - match:
          severity: warning
        receiver: 'slack'
    receivers:
    - name: 'default'
      slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK'
        channel: '#alerts'
    - name: 'pagerduty'
      pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

## Centralized Logging

### 1. ELK Stack Setup

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: logstash-config
data:
  logstash.conf: |
    input {
      tcp {
        port => 5000
        codec => json
      }
    }
    filter {
      mutate {
        add_field => { "[@metadata][index_name]" => "logs-%{+YYYY.MM.dd}" }
      }
    }
    output {
      elasticsearch {
        hosts => ["elasticsearch:9200"]
        index => "%{[@metadata][index_name]}"
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
        ports:
        - containerPort: 9200
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kibana
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: kibana
        image: docker.elastic.co/kibana/kibana:8.0.0
        ports:
        - containerPort: 5601
```

## Application Performance Monitoring

### 1. Custom APM Metrics

```python
class APMMetrics:
    def __init__(self):
        self.workflow_latency = Histogram(
            'workflow_latency_ms',
            'Workflow execution latency',
            buckets=[100, 500, 1000, 5000, 10000]
        )
        self.case_processing_time = Histogram(
            'case_processing_time_ms',
            'Case processing time'
        )
        self.queue_wait_time = Histogram(
            'queue_wait_time_ms',
            'Task queue waiting time'
        )
    
    def record_workflow_execution(self, duration_ms, status):
        self.workflow_latency.observe(duration_ms)
    
    def record_case_processing(self, duration_ms):
        self.case_processing_time.observe(duration_ms)
```

## SLOs and KPIs

### 1. Service Level Objectives

- **Availability**: 99.9% uptime
- **Latency**: p95 < 500ms, p99 < 1s
- **Error Rate**: < 0.1%
- **Throughput**: 10,000+ requests/sec

### 2. Key Performance Indicators

- **Case Resolution Time**: < 5 minutes
- **Workflow Success Rate**: > 99.5%
- **Task Processing Latency**: < 100ms
- **Queue Processing Rate**: > 1000 tasks/min

## Dashboard Access

- **Grafana**: http://grafana.example.com
- **Jaeger UI**: http://jaeger.example.com:16686
- **Kibana**: http://kibana.example.com:5601
- **Prometheus**: http://prometheus.example.com:9090

## Next Steps
1. Deploy Jaeger infrastructure
2. Configure OpenTelemetry instrumentation
3. Create Grafana dashboards
4. Set up alerting rules
5. Configure logging pipeline
6. Establish runbooks and playbooks
7. Perform end-to-end testing
8. Complete project and documentation
