# Phase 6: ML Infrastructure Preparation Implementation Guide

## Overview
This phase establishes the foundational machine learning infrastructure for Q1 2026 deployment, including feature stores, model serving, experiment tracking, and data pipeline orchestration.

## Feature Store Implementation

### Feast Setup
```yaml
Feature Store Architecture:
- Feast as feature platform
- PostgreSQL offline store
- Redis online store
- Feature registry in S3
- Real-time and batch feature serving
```

### Installation & Configuration
```bash
# Install Feast
pip install feast[postgres,redis,s3]

# Initialize Feast project
feast init ci_failure_agent_feast
cd ci_failure_agent_feast

# Update feature_store.yaml
cat > feature_store.yaml <<EOF
project: ci_failure_agent
registry: s3://ci-failure-agent-feast/registry.db
provider: local
offline_store:
  type: postgres
  host: postgres.ci-failure-agent.svc.cluster.local
  port: 5432
  database: ci_failure_agent_feast
  user: feast_user
  password: ${FEAST_DB_PASSWORD}
online_store:
  type: redis
  connection_string: redis-cluster.ci-failure-agent.svc.cluster.local:6379
EOF
```

### Feature Definition
```python
# features/ci_failure_features.py
from datetime import timedelta
from feast import Entity, Feature, FeatureView, ValueType
from feast.data_sources import PostgreSQLSource

ci_run = Entity(
    name="ci_run",
    value_type=ValueType.STRING,
    description="CI pipeline run identifier"
)

ci_run_source = PostgreSQLSource(
    database="ci_failure_agent_feast",
    schema="public",
    table="ci_runs",
    timestamp_field="created_timestamp"
)

ci_run_features = FeatureView(
    name="ci_run_features",
    entities=["ci_run"],
    features=[
        Feature(name="pipeline_duration_seconds", dtype=ValueType.FLOAT),
        Feature(name="test_success_rate", dtype=ValueType.FLOAT),
        Feature(name="artifact_size_mb", dtype=ValueType.FLOAT),
        Feature(name="resource_utilization", dtype=ValueType.FLOAT),
    ],
    online=True,
    source=ci_run_source,
    ttl=timedelta(days=30),
)
```

## Model Serving Infrastructure

### KServe Installation
```bash
# Install KServe operator
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.11.0/kserve.yaml

# Verify installation
kubectl get crd | grep inference
```

### Model Deployment
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: ci-failure-predictor
  namespace: ci-failure-agent
spec:
  predictor:
    model:
      modelFormat:
        name: sklearn
      storageUri: s3://ci-failure-agent-models/ci-failure-predictor/v1
    resources:
      requests:
        cpu: "500m"
        memory: "1Gi"
      limits:
        cpu: "1000m"
        memory: "2Gi"
  explainer:
    model:
      modelFormat:
        name: sklearn
      storageUri: s3://ci-failure-agent-models/ci-failure-explainer/v1
```

## Experiment Tracking

### MLflow Setup
```bash
# Install MLflow
pip install mlflow[postgresql]

# Start MLflow server
mlflow server \
  --backend-store-uri postgresql://mlflow:password@postgres:5432/mlflow \
  --default-artifact-root s3://ci-failure-agent-artifacts \
  --host 0.0.0.0 \
  --port 5000
```

### Experiment Tracking Code
```python
# ml_pipeline/experiment_tracker.py
import mlflow
from mlflow.models.signature import infer_signature
import sklearn.metrics as metrics

mlflow.set_tracking_uri("http://mlflow.ci-failure-agent:5000")
mlflow.set_experiment("ci_failure_prediction")

with mlflow.start_run(run_name="baseline_model"):
    # Train model
    model.fit(X_train, y_train)
    
    # Log parameters
    mlflow.log_param("max_depth", 10)
    mlflow.log_param("learning_rate", 0.01)
    
    # Log metrics
    predictions = model.predict(X_test)
    accuracy = metrics.accuracy_score(y_test, predictions)
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("f1_score", metrics.f1_score(y_test, predictions))
    
    # Log model
    signature = infer_signature(X_train, model.predict(X_train))
    mlflow.sklearn.log_model(model, "model", signature=signature)
```

## Data Pipeline Orchestration

### Airflow DAG Setup
```python
# airflow/dags/ci_failure_pipeline.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.models import Variable

default_args = {
    'owner': 'ml-platform',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'ci_failure_prediction_pipeline',
    default_args=default_args,
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    catchup=False,
)

def extract_features():
    """Extract features from raw data"""
    # Feature engineering logic
    pass

def train_model():
    """Train ML model"""
    # Model training logic
    pass

def evaluate_model():
    """Evaluate model performance"""
    # Model evaluation logic
    pass

def deploy_model():
    """Deploy model to serving"""
    # Deployment logic
    pass

extract_task = PythonOperator(
    task_id='extract_features',
    python_callable=extract_features,
    dag=dag,
)

train_task = KubernetesPodOperator(
    task_id='train_model',
    image='ci-failure-agent/ml-trainer:latest',
    name='train-model-pod',
    namespace='ci-failure-agent',
    dag=dag,
)

evaluate_task = PythonOperator(
    task_id='evaluate_model',
    python_callable=evaluate_model,
    dag=dag,
)

deploy_task = PythonOperator(
    task_id='deploy_model',
    python_callable=deploy_model,
    dag=dag,
)

extract_task >> train_task >> evaluate_task >> deploy_task
```

## Feature Store Testing

### Unit Tests
```python
# tests/test_features.py
import pytest
from feast import FeatureStore

@pytest.fixture
def feature_store():
    return FeatureStore(repo_path=".")

def test_feature_retrieval(feature_store):
    """Test feature retrieval from store"""
    entity_df = pd.DataFrame({"ci_run": ["run_123", "run_456"]})
    
    features = feature_store.get_online_features(
        features=["ci_run_features:pipeline_duration_seconds"],
        entity_rows=entity_df.to_dict(orient='records'),
    )
    
    assert features is not None
    assert len(features['results']) == 2
```

## Infrastructure Manifests

### Kubernetes Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ci-failure-ml
  labels:
    name: ci-failure-ml
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ml-quota
  namespace: ci-failure-ml
spec:
  hard:
    requests.cpu: "20"
    requests.memory: "40Gi"
    limits.cpu: "40"
    limits.memory: "80Gi"
```

## Monitoring ML Pipeline

### Prometheus Rules
```yaml
- alert: ModelAccuracyDegradation
  expr: |
    rate(model_accuracy[7d]) < 0.85
  for: 1h
  annotations:
    summary: "Model accuracy degradation detected"

- alert: FeatureStoreLatency
  expr: |
    feature_store_query_duration_seconds_p99 > 1.0
  for: 5m
  annotations:
    summary: "Feature store query latency high"
```

## Deliverables

✓ Feast feature store deployment
✓ KServe model serving infrastructure
✓ MLflow experiment tracking setup
✓ Airflow data pipeline orchestration
✓ Feature engineering modules
✓ Model training pipelines
✓ Kubernetes manifests for ML services
✓ Monitoring and alerting rules
✓ Testing frameworks for ML components

## Next Steps

Phase 6.1: Q1 2026 ML Production Deployment
- Production ML model deployment
- Real-time prediction serving
- Model monitoring and retraining
- Feature pipeline scaling
