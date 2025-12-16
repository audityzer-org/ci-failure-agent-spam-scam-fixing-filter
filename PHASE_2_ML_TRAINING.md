# Phase 2: ML Model Training (MVP + 3 months)
## Building & Deploying a Ranking Model

---

## Overview

Phase 2 transitions from rule-based to **ML-powered ranking**. We train a LightGBM model on 30 days of proposition click logs to predict user acceptance probability.

**Timeline**: Months 2-3  
**Team**: ML/Data Engineers (lead), Backend (support)  
**Deliverable**: Production-ready ranking model with <100ms inference latency  

---

## Phase 2 Stages

### Stage 2.1: Data Collection & Pipeline (Week 1-2)

**Objective**: Gather 30 days of clean training data.

**Tasks**:
1. **Verify logging infrastructure**
   ```sql
   -- Check proposition_logs table exists with data
   SELECT COUNT(*), DATE(created_at) 
   FROM proposition_logs 
   WHERE created_at > NOW() - INTERVAL 30 DAY
   GROUP BY DATE(created_at);
   ```

2. **Data extraction script** (`scripts/extract_ml_data.py`)
   ```python
   import pandas as pd
   from sqlalchemy import create_engine
   
   engine = create_engine(os.getenv('DATABASE_URL'))
   
   query = """
   SELECT 
     alert_id, alert_type, severity,
     user_id, action_taken, resolution_time_seconds,
     model_source, confidence_score, created_at
   FROM proposition_logs
   WHERE created_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
   """
   
   df = pd.read_sql(query, engine)
   df.to_parquet('data/proposition_logs_30d.parquet')
   print(f"Extracted {len(df)} rows")
   ```

3. **Data validation**
   - [ ] No NaN values in critical columns
   - [ ] No data leakage (future timestamps)
   - [ ] Target variable balanced (% accepted vs ignored)
   - [ ] At least 10K examples per alert_type

### Stage 2.2: Feature Engineering (Week 2-3)

**Objective**: Create features for ML model.

**Features**:

```python
import pandas as pd
import numpy as np

df = pd.read_parquet('data/proposition_logs_30d.parquet')

# 1. Target variable: Binary classification
df['target'] = (df['action_taken'] == 'accepted').astype(int)

# 2. Alert features
df['alert_type_encoded'] = pd.Categorical(df['alert_type']).codes
df['severity_encoded'] = pd.Categorical(df['severity'], 
                                        categories=['low', 'medium', 'high', 'critical']).codes

# 3. User features
user_stats = df.groupby('user_id').agg({
    'resolution_time_seconds': ['mean', 'std', 'median'],
    'target': 'mean'  # User's historical acceptance rate
}).reset_index()
user_stats.columns = ['user_id', 'user_avg_resolution_time', 'user_std_resolution_time',
                       'user_median_resolution_time', 'user_acceptance_rate']
df = df.merge(user_stats, on='user_id', how='left')

# 4. Global/temporal features
alert_stats = df.groupby('alert_type').agg({
    'target': 'mean',  # Alert type's global acceptance rate
    'alert_id': 'count'  # Alert type frequency
}).reset_index().rename(columns={'target': 'alert_acceptance_rate', 'alert_id': 'alert_frequency'})
df = df.merge(alert_stats, on='alert_type', how='left')

# 5. Time features
df['hour'] = pd.to_datetime(df['created_at']).dt.hour
df['dayofweek'] = pd.to_datetime(df['created_at']).dt.dayofweek
df['is_weekend'] = (df['dayofweek'] >= 5).astype(int)

# 6. Cyclical encoding for hour (sine/cosine)
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

df = df.fillna(0)  # Fill NaN with 0

print(f"Features created: {df.shape[1]} columns")
df.to_parquet('data/features_engineered.parquet')
```

**Feature Summary Table**:

| Feature | Type | Source | Notes |
|---------|------|--------|-------|
| `alert_type_encoded` | Categorical | Alert | One-hot encoded |
| `severity_encoded` | Ordinal | Alert | 0=low, 1=med, 2=high, 3=crit |
| `user_avg_resolution_time` | Numerical | User history | Minutes |
| `user_acceptance_rate` | Numerical | User history | 0-1 |
| `alert_acceptance_rate` | Numerical | Global | Alert type popularity |
| `alert_frequency` | Numerical | Global | Count in dataset |
| `hour_sin`, `hour_cos` | Numerical | Temporal | Cyclical encoding |
| `is_weekend` | Binary | Temporal | Weekend vs weekday |

### Stage 2.3: Model Training (Week 3)

**Objective**: Train & validate LightGBM ranking model.

**Training Script** (`scripts/train_model.py`):

```python
import pandas as pd
import numpy as np
from lightgbm import LGBMRanker
from sklearn.model_selection import train_test_split
from sklearn.metrics import ndcg_score, auc, roc_auc_score
import joblib

# Load data
df = pd.read_parquet('data/features_engineered.parquet')

# Feature selection
feature_cols = [
    'alert_type_encoded', 'severity_encoded',
    'user_avg_resolution_time', 'user_acceptance_rate',
    'alert_acceptance_rate', 'alert_frequency',
    'hour_sin', 'hour_cos', 'is_weekend'
]

X = df[feature_cols]
y = df['target']

# Temporal split (preserve chronology)
train_size = int(0.7 * len(df))
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# Group by alert_id for ranking
alert_groups_train = df[:train_size].groupby('alert_id').size().values
alert_groups_test = df[train_size:].groupby('alert_id').size().values

# Train model
model = LGBMRanker(
    objective='binary',
    metric='ndcg',
    n_estimators=100,
    num_leaves=31,
    learning_rate=0.05,
    random_state=42,
    n_jobs=-1,
    verbose=10
)

model.fit(
    X_train, y_train,
    group=alert_groups_train,
    eval_set=[(X_test, y_test)],
    eval_group=[alert_groups_test],
    callbacks=[
        LGBMRanker.early_stopping(50),
        LGBMRanker.log_evaluation(period=10)
    ]
)

# Evaluate
y_pred = model.predict(X_test)

ndcg_3 = ndcg_score([alert_groups_test], [y_pred[:len(alert_groups_test)]], k=3)
auc_score = roc_auc_score(y_test, y_pred)

print(f"NDCG@3: {ndcg_3:.4f}")
print(f"AUC-ROC: {auc_score:.4f}")

# Save model
joblib.dump(model, 'models/ranking_model_v1.pkl')
print("Model saved to models/ranking_model_v1.pkl")

# Feature importance
importances = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\nTop 5 features:")
print(importances.head())
```

**Success Criteria**:
- [ ] NDCG@3 ≥ 0.65
- [ ] AUC-ROC ≥ 0.72
- [ ] No data leakage detected
- [ ] Training time < 10 minutes
- [ ] Model size < 50MB

### Stage 2.4: Model Deployment (Week 4)

**Objective**: Deploy model to production.

**Steps**:

1. **Model versioning** (MLflow)
   ```bash
   mlflow models log-model \
     --model-uri models/ranking_model_v1.pkl \
     --run-id <run_id> \
     --artifact-path models
   ```

2. **Create model serving endpoint** (`src/ml_ranking.py`)
   ```python
   import joblib
   from fastapi import FastAPI
   import numpy as np
   
   app = FastAPI()
   model = joblib.load('models/ranking_model_v1.pkl')
   
   @app.post("/rank")
   async def rank_propositions(features: dict):
       X = np.array([features.values()])
       scores = model.predict(X)
       return {"rank_score": float(scores[0])}
   
   @app.get("/health")
   async def health():
       return {"status": "ok", "model": "ranking_v1"}
   ```

3. **Integration into orchestration_engine.py**
   ```python
   from src.ml_ranking import model as ranking_model
   
   def rank_propositions_ml(suggestions, features):
       """Rank using ML model instead of rules."""
       scores = ranking_model.predict([features])
       for sugg, score in zip(suggestions, scores):
           sugg.ml_score = score
       return sorted(suggestions, key=lambda s: s.ml_score, reverse=True)
   ```

4. **Deployment checklist**
   - [ ] Model loads in <1s
   - [ ] Prediction latency p95 < 50ms
   - [ ] 100 QPS load test passes
   - [ ] Monitoring/alerting configured
   - [ ] Rollback plan documented

### Stage 2.5: A/B Testing & Monitoring (Weeks 3-4)

**A/B Test Setup**:

```python
# In orchestration_engine.py
def get_propositions_with_variant(alert, user_id, experiment_id=None):
    # Determine variant: rule-based (control) vs ML-ranking (treatment)
    variant = hash(user_id) % 2  # 50/50 split
    
    base_propositions = get_rule_based_propositions(alert)
    
    if variant == 0:
        # Control: use rule-based ranking
        log_event("experiment", {"user_id": user_id, "variant": "control"})
        return base_propositions
    else:
        # Treatment: use ML ranking
        try:
            ranked = rank_propositions_ml(base_propositions, features)
            log_event("experiment", {"user_id": user_id, "variant": "treatment"})
            return ranked
        except Exception as e:
            # Fallback to rules if ML fails
            log_event("ml_error", {"error": str(e)})
            return base_propositions
```

**Metrics to Track**:
- TTIA (Time-To-Action) by variant
- Acceptance Rate by variant
- CTR by variant
- Model inference latency
- Error rate
- User satisfaction (survey)

---

## Tech Stack (Phase 2)

| Component | Tool | Version |
|-----------|----|----------|
| Data Processing | `pandas` | 2.0+ |
| ML Model | `lightgbm` | 4.0+ |
| Experiment Tracking | `mlflow` | 2.0+ |
| Model Serving | `fastapi` + `uvicorn` | Latest |
| Monitoring | `prometheus` | Latest |

**Installation**:
```bash
pip install -r requirements-ml.txt
# Contents: pandas, scikit-learn, lightgbm, mlflow, fastapi, prometheus-client
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Low NDCG (<0.60) | Add more features, adjust learning rate, increase data |
| High prediction latency (>100ms) | Reduce tree depth, use batch prediction, quantize model |
| Model overfitting | Reduce n_estimators, increase reg_l1/reg_l2, more data |
| Data leakage | Check for future timestamps, remove future-engineered features |

---

## Success Criteria (Phase 2)

✅ **Must have**:
- NDCG@3 ≥ 0.65
- Inference latency < 100ms (p95)
- A/B test shows +10% TTIA improvement

✅ **Nice to have**:
- Interpretability report (feature importance)
- Auto-retraining pipeline
- Multi-model ensemble

---

**Next**: Phase 3 (LLM + Hybrid Ranking, Month 6)
