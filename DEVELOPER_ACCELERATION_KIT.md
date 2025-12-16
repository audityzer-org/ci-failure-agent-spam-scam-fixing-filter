# Developer Acceleration Kit
## Essential Tools & Guides for Safe, Fast Development

---

## 🎯 For Every Developer

### Quick Start (5 min)
```bash
# Clone & setup
git clone https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter.git
cd ci-failure-agent-spam-scam-fixing-filter

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests locally
pytest tests/ -v --cov=src/ --tb=short

# Run linting
flake8 src/ tests/ && mypy src/ && black --check src/ tests/
```

### Git Workflow (Safe & Fast)
```bash
# Branch naming: feature/description or fix/issue-id
git checkout -b feature/predictive-engine-v2

# Work locally with auto-tests
pytest tests/test_predictive_suggestions_*.py -v --watch

# Commit with conventional format
git commit -m "feat(predictive): add confidence filtering"

# Push & create PR (CI runs automatically)
git push origin feature/predictive-engine-v2
# Then create PR on GitHub

# Before merging:
# ✅ All tests pass (GitHub Actions)
# ✅ Code review approved
# ✅ No conflicts with main
```

---

## 👨‍💻 By Role

### **Backend Engineers**

**Tools & Setup:**
- Python 3.11+ (required)
- `pytest` - unit testing
- `black` - code formatting (auto)
- `mypy` - type checking
- `flake8` - linting
- Redis (for local caching tests)

**Essential Commands:**
```bash
# Local dev server with auto-reload
python -m uvicorn src.api.main:app --reload

# Test specific module
pytest tests/test_predictive_suggestions_engine.py -v

# Check coverage
pytest --cov=src/predictive_suggestions --cov-report=html
# Then open htmlcov/index.html

# Type checking
mypy src/predictive_suggestions/ --strict

# Format code (auto-fix)
black src/ tests/
```

**Safety Checklist Before PR:**
- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] No type errors (`mypy src/ --strict`)
- [ ] Code formatted (`black src/`)
- [ ] Linting passes (`flake8 src/`)
- [ ] New tests added for new code
- [ ] Docstrings updated
- [ ] No secrets in code (use `.env.example`)

**Common Errors & Fixes:**
| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'src'` | Add `PYTHONPATH=.` before running commands |
| `pytest: command not found` | `pip install -r requirements-dev.txt` |
| `mypy: errors detected` | Check `# type: ignore` comments or fix types |

---

### **ML/Data Engineers**

**Tools & Setup:**
- Python 3.11+
- `scikit-learn`, `xgboost`, `lightgbm` (Phase 2)
- `pandas` - data handling
- `jupyter` - notebooks
- `mlflow` - experiment tracking (Phase 2+)

**Essential Commands:**
```bash
# Create isolated ML environment
python -m venv venv_ml
source venv_ml/bin/activate  # or `venv_ml\Scripts\activate` on Windows

# Install ML dependencies
pip install -r requirements-ml.txt

# Training notebook template
jupyter notebook notebooks/phase_2_model_training.ipynb

# Log experiments (Phase 2)
mlflow ui  # Track experiments at localhost:5000
```

**Data Pipeline (Phase 2):**
```python
# Load proposition logs from DB
df = pd.read_sql(
    "SELECT * FROM proposition_logs WHERE created_at > CURRENT_DATE - INTERVAL 30 DAY",
    connection
)

# Feature engineering
df['user_expertise'] = df.groupby('user_id')['resolution_time'].transform('mean') / 60.0
df['alert_frequency'] = df.groupby('alert_type')['created_at'].transform('count')

# Train model
from lightgbm import LGBMRanker
model = LGBMRanker(random_state=42, n_jobs=-1)
model.fit(X_train, y_train, group=group_train)

# Evaluate
from sklearn.metrics import ndcg_score
ndcg = ndcg_score([group_test], [model.predict(X_test)])
print(f"NDCG@3: {ndcg:.4f}")
```

**Output & Validation:**
- [ ] Model metrics logged to MLflow
- [ ] Feature importance documented
- [ ] Cross-validation scores computed
- [ ] Prediction latency < 100ms (p95)
- [ ] Data leakage check passed

---

### **Frontend Engineers**

**Tools & Setup:**
- Node 18+ & npm/yarn
- React / Next.js (latest)
- TypeScript
- Vitest / Jest for unit tests
- Playwright for E2E

**Essential Commands:**
```bash
# Setup
cd ui && npm install

# Dev server
npm run dev  # localhost:3000

# Build & test
npm run build
npm run test

# Component integration with backend
# See ui/src/components/PropositionCard.tsx for example
```

**UI Component Spec:**
```tsx
// PropositionCard - displays AI suggestion
<PropositionCard
  proposition={{
    id: "prop_123",
    title: "Fix Assertion Error",
    description: "Review test expectations...",
    actions: ["Run tests locally", "Fix logic"],
    confidence: 0.95,
    severity: "high"
  }}
  onAccept={() => logPropositionClick("accepted")}
  onIgnore={() => logPropositionClick("ignored")}
/>
```

**Tracking Events:**
- Log `proposition_shown` on render
- Log `proposition_clicked` on interaction
- Send to backend for ML training

---

### **DevOps/Infrastructure**

**Tools & Setup:**
- Docker & Docker Compose
- Kubernetes (production)
- Terraform / AWS CDK
- GitHub Actions (CI/CD)

**Essential Commands:**
```bash
# Local dev with Docker
docker-compose up -d  # Start all services

# Check service health
curl -s http://localhost:8000/health | jq

# View logs
docker-compose logs -f orchestration_engine

# Deploy to staging
git push origin main  # Triggers GitHub Actions
# Check: github.com/.../actions for deployment status

# Production deployment (manual)
kubectl apply -f k8s/production-deploy.yml
```

**Deployment Checklist:**
- [ ] All tests pass in CI
- [ ] Database migrations run
- [ ] Secrets rotated (AWS Secrets Manager)
- [ ] Monitoring alerts configured (CloudWatch)
- [ ] Load testing done (target: 100 req/s)
- [ ] Rollback plan documented

---

### **Security/Compliance**

**Tools & Setup:**
- `bandit` - code security scan
- `safety` - dependency vulnerabilities
- `trivy` - container scanning
- OWASP guidelines

**Essential Commands:**
```bash
# Scan code for security issues
bandit -r src/

# Check dependencies
safety check -r requirements.txt

# Scan Docker image
trivy image ci-failure-agent:latest
```

**Security Checklist:**
- [ ] No hardcoded secrets (use `.env` or AWS Secrets)
- [ ] No PII in logs (user_id only, never email)
- [ ] Input validation on all APIs
- [ ] SQL injection prevention (use ORM/parameterized)
- [ ] Rate limiting enabled
- [ ] HTTPS enforced in production
- [ ] Encryption at rest for sensitive data

---

## 📊 Monitoring & Debugging

### Local Testing
```bash
# Run all tests with coverage
pytest tests/ -v --cov=src/ --cov-report=term-missing

# Run specific test class
pytest tests/test_predictive_suggestions_engine.py::TestSuggestionEngine::test_generate_suggestions_ci_failure -v

# Debug with pdb
pytest tests/ --pdb  # Drops into debugger on failure
```

### Production Debugging
- **Logs**: CloudWatch or Stackdriver
- **Metrics**: Prometheus (latency, error rate, cache hit ratio)
- **Traces**: X-Ray or Jaeger
- **Alerts**: SNS topic `predictive-propositions-alerts`

### Key Metrics to Monitor
- **Latency**: p95 < 100ms, p99 < 200ms
- **Error Rate**: < 0.1%
- **Cache Hit Ratio**: > 85%
- **Model Accuracy**: precision@3 > 70%
- **User Acceptance**: CTR > 15%

---

## 🚀 Development Sprint Workflow

### Daily (Each Dev)
1. **Start of day**:
   ```bash
   git fetch origin
   git rebase origin/main  # Keep branch fresh
   ```

2. **Work on task**:
   ```bash
   pytest tests/ -v --watch  # Auto-run tests on file change
   ```

3. **End of day**:
   ```bash
   git add .
   git commit -m "progress: [task-id] partial implementation"
   git push  # Backup to GitHub
   ```

### Weekly (Team)
1. **Monday**: Sprint planning, assign tasks
2. **Wed/Thu**: Code review checkpoints
3. **Friday**: Demo, retrospective, next week planning

---

## 📚 Documentation

**Essential Docs:**
- `README.md` - Project overview
- `PREDICTIVE_PROPOSITIONS_SPEC.md` - Feature spec
- `PREDICTIVE_SUGGESTIONS_MODULE.md` - Module design
- `API_DOCUMENTATION.md` - API endpoints
- `PHASE_*_*.md` - Phase-specific guides

**Add Docs When:**
- Adding new API endpoint → Update API_DOCUMENTATION.md
- Adding new config option → Update README
- Changing DB schema → Update data/schema.md
- New deployment process → Update DevOps guide

---

## 🆘 Getting Help

### For Backend Issues
→ DM `@backend-lead` or comment in `#backend` Slack

### For ML/Data Issues
→ Check `notebooks/` examples or ask `@data-lead`

### For Infrastructure Issues
→ See `k8s/` folder or message `@devops-lead`

### For Security Issues
→ Email security@audityzer.org (don't post publicly)

---

## 🎓 Learning Resources

- **Python/Testing**: [Pytest docs](https://pytest.org/)
- **ML/Ranking**: [LightGBM LambdaMART](https://lightgbm.readthedocs.io/)
- **Type Safety**: [Mypy handbook](https://mypy.readthedocs.io/)
- **CI/CD**: [GitHub Actions docs](https://docs.github.com/en/actions)
- **Security**: [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

**Last Updated**: Dec 2025  
**Status**: ✅ Phase 1 MVP + CI/CD  
**Next**: Phase 2 ML Training (Jan 2025)
