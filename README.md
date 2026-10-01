# FlightOps Sentinel

FlightOps Sentinel is a production-oriented machine-learning platform that predicts whether a scheduled flight will depart at least 15 minutes late.

The MVP has one model and one prediction horizon: departure-delay risk at T-24h, meaning 24 hours before scheduled departure.

## Documentation

- [Product requirements](prd.md)
- [Architecture](architecture.md)
- [Implementation roadmap](todo.md)
- [Repository instructions](AGENTS.md)
- [Clean Code review and maintenance checks](docs/clean-code-review.md)

## Technology Direction

- PostgreSQL for source and derived relational data
- Airflow for scheduled data and ML workflows
- MLflow for experiment tracking and model registry
- FastAPI for prediction serving
- Docker and Kubernetes for runtime environments
- Prometheus, Grafana, and Alertmanager for observability
- GitHub Actions for CI/CD

## Local Development

Python 3.12.10 is the pinned project version, recorded in `.python-version`. If using pyenv, install it once and let pyenv select it automatically inside this repository:

```powershell
pyenv install 3.12.10
```

After Python is available, create and activate a virtual environment, then install the development dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Copy the example configuration before running any service:

```powershell
Copy-Item .env.example .env
```

The values in `.env.example` are local placeholders only. Do not commit `.env` or credentials.

For the local PostgreSQL source database and MLflow infrastructure, follow the [local source database runbook](docs/runbooks/local-source-database.md).
For Docker services, Airflow, smoke testing, and troubleshooting, follow the [local platform runbook](docs/runbooks/local-platform.md).
Prometheus, Grafana, Alertmanager, metrics, alerts, and operational responses are documented in the [observability runbook](docs/runbooks/observability.md).
GitHub Actions checks, immutable GHCR images, staging deployment, and the production approval gate are documented in [CI/CD](docs/ci-cd.md).
The local Kubernetes deployment, image loading, rollout, and rollback workflow is documented in the [Minikube runbook](docs/runbooks/minikube.md).
The restored source snapshot is described in the [source data inventory](docs/source-data-inventory.md).
The staging and label contract is described in the [flight-delay data contract](docs/data-contract.md).
Derived tables and fields are listed in the [data dictionary](docs/data-dictionary.md).
The T-24h feature availability rules are documented in the [feature contract](docs/feature-contract.md).
The completed Phase 3 validation is recorded in the [leakage audit](docs/leakage-audit.md).
The baseline model and chronological evaluation design are documented in [baseline evaluation](docs/baseline-evaluation.md).
The actual baseline comparison and promotion decision are recorded in [baseline results](docs/baseline-results.md).
MLflow tracking, registry, and promotion rules are documented in [MLflow lifecycle](docs/mlflow-lifecycle.md).
The prediction endpoint behavior is documented in the [API contract](docs/api-contract.md).
The staged candidate training, Optuna tuning, calibration, and MLflow workflow is documented in the [training pipeline](docs/training-pipeline.md).

## Quality Checks

```powershell
ruff check .
ruff format --check .
mypy src
pytest
```

## Current Status

Training records `git_revision=unavailable` when Git or repository metadata is unavailable. A truncated or invalid approved-model artifact produces the documented model-unavailable response instead of an internal server error. See [the Clean Code review](docs/clean-code-review.md) for the remaining design and integration limits.

Local data, artifacts, virtual environments, caches, credentials, and downloaded Kubernetes tools in `.tools/` are excluded from Git. Keep deployment configuration in source and provide runtime credentials through `.env` or the deployment secret mechanism.
