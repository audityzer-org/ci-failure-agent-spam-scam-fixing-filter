# CI Failure Agent - Spam/Scam Detection Filter

**Agentic AI system for automated CI/CD failure analysis and workflow optimization using multi-agent architecture**

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](#)
[![Status](https://img.shields.io/badge/status-Production%20Ready-success)](https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter/releases/tag/v1.0.0)

## Overview

This project provides an **intelligent CI/CD failure analysis and automatic fixing system** combined with **spam/scam detection capabilities**. It uses:

- **Predictive Suggestions Engine**: ML-powered recommendations for CI failures and spam incidents
- **Orchestration Engine**: Multi-phase rule-based and ML-driven decision making
- **Multi-Agent Architecture**: Specialized agents for different aspects of analysis
- **Production Deployment**: Ready for Kubernetes, AWS EKS, and containerized environments

## Key Features

✅ **Automated CI Failure Detection**: Analyzes logs and identifies root causes  
✅ **Spam/Scam Detection**: Identifies malicious patterns and suspicious activities  
✅ **ML-Powered Ranking**: LightGBM-based ranking for suggestions (Phase 2)  
✅ **Rule-Based Engine**: Comprehensive rule library for quick analysis  
✅ **Production Ready**: Full K8s deployment, monitoring, and scaling  
✅ **Comprehensive Testing**: Unit, integration, and E2E test coverage  
✅ **Rich Documentation**: Architecture guides, deployment playbooks, and developer guides

## Project Structure

```
.
├── src/                           # Core source code
│   ├── predictive_suggestions/   # Suggestion engine modules
│   ├── orchestration_engine.py   # Main orchestration logic
│   └── ...
├── services/                      # Microservices
│   ├── audit-trail-aggregator/   # Audit logging service
│   └── ...
├── tests/                         # Test suites
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── conftest.py              # Pytest configuration
├── k8s/                          # Kubernetes manifests
├── terraform/                    # Infrastructure as Code
├── docs/                         # Documentation
└── .github/workflows/            # CI/CD pipelines
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Kubernetes cluster (optional, for production)
- pip and virtual environment

### Installation

```bash
# Clone repository
git clone https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter.git
cd ci-failure-agent-spam-scam-fixing-filter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/unit/ -v  # Unit tests
pytest tests/integration/ -v  # Integration tests

# With coverage report
pytest tests/ --cov=src --cov=services --cov-report=html
```

### Local Development

```bash
# Start services locally
docker-compose up -d

# Run orchestration engine
python -m src.orchestration_engine

# Access API documentation
open http://localhost:8000/docs
```

## Development Phases

### Phase 1: Foundation (✅ Complete)
- Rule-based suggestion engine
- Orchestration framework
- Comprehensive unit tests
- Initial documentation

### Phase 2: ML Training (✅ Complete)
- LightGBM ranking model
- Feature engineering pipeline
- A/B testing infrastructure
- Production deployment ready

### Phase 3: API & Performance (✅ Complete)
- REST API with FastAPI
- Response caching (Redis)
- Performance optimization
- Production deployment guide

### Phase 4+: Advanced Features (In Progress)
- LLM integration
- Advanced analytics
- Multi-model ensemble
- Auto-retraining pipeline

## Architecture

**Multi-Agent System**:
1. **Analyzer Agent**: Examines CI logs and failure patterns
2. **Suggester Agent**: Generates fix recommendations
3. **Validator Agent**: Verifies suggestions quality
4. **Decision Agent**: Applies ML ranking and selects best action
5. **Executor Agent**: Implements the recommended fix

**Tech Stack**:
- **Backend**: Python 3.11, FastAPI, SQLAlchemy
- **ML**: LightGBM, scikit-learn, pandas
- **Data**: PostgreSQL, Redis
- **Containers**: Docker, Kubernetes
- **Monitoring**: Prometheus, Grafana
- **CI/CD**: GitHub Actions

## Documentation

📖 **Key Documents**:
- [Architecture & Design Decisions](ARCHITECTURE_AND_DESIGN_DECISIONS.md)
- [Phase 2: ML Training Guide](PHASE_2_ML_TRAINING.md)
- [API Documentation](PHASE_3_5_API_DOCUMENTATION.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Developer Acceleration Kit](DEVELOPER_ACCELERATION_KIT.md)
- [Operations & Maintenance Manual](OPERATIONS_AND_MAINTENANCE_MANUAL.md)

## Testing & CI/CD

**Test Coverage**:
- ✅ Unit Tests: `tests/unit/` (19+ test files)
- ✅ Integration Tests: `tests/integration/` (5+ test files)
- ✅ E2E Tests: `tests/test_e2e_production.py`
- ✅ Load Tests: `tests/test_load.py`

**CI/CD Pipeline**: `.github/workflows/tests.yml`
- Runs on: Python 3.11, 3.12
- Includes: Unit tests, integration tests, linting, coverage
- Status: ✅ All passing

## Installation & Contribution

### For Contributors

```bash
# Setup development environment
pip install -r requirements-dev.txt

# Run linting & formatting
flake8 src/ services/ tests/
mypy src/ --ignore-missing-imports
black src/ services/ tests/

# Create a feature branch
git checkout -b feature/your-feature

# Commit with semantic messages
git commit -m "feat: describe your change"

# Push and create PR
git push origin feature/your-feature
```

## Deployment

### Docker

```bash
docker build -t ci-failure-agent:latest .
docker run -p 8000:8000 ci-failure-agent:latest
```

### Kubernetes

```bash
kubectl apply -f k8s/
kubectl port-forward svc/ci-failure-agent 8000:8000
```

### AWS (Render, EKS, EC2)

See [AWS Deployment Guide](AWS_EKS_DEPLOYMENT_GUIDE.md) and [Render Deployment](DEPLOYMENT_SUCCESS_AWS_EC2.md)

## Known Issues & Troubleshooting

**Test Import Errors Fixed** ✅
- Added `conftest.py` with proper sys.path configuration
- Added `__init__.py` files in `tests/` and `tests/unit/`
- All module imports now working correctly

**YAML Syntax Fixed** ✅
- Fixed `.github/workflows/tests.yml` line 100 error
- Workflow now runs successfully

For more help: See [Troubleshooting Guide](OPERATIONS_AND_MAINTENANCE_MANUAL.md#troubleshooting)

## Performance Metrics

- **Suggestion Generation**: < 100ms (p95)
- **ML Model Inference**: < 50ms (p95)
- **API Response Time**: < 200ms (p95)
- **System Uptime**: 99.9%+ (SLA)

## Support & Community

- 📧 **Issues**: [GitHub Issues](https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter/discussions)
- 📖 **Wiki**: [Project Wiki](https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter/wiki)

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details

## Release Notes

**v1.0.0** - [Production Ready Release](https://github.com/audityzer-org/ci-failure-agent-spam-scam-fixing-filter/releases/tag/v1.0.0)
- Complete Phase 1-3 implementation
- Production deployment ready
- 202+ commits
- Comprehensive documentation

---

**Last Updated**: December 16, 2025 | **Status**: Production Ready ✅
