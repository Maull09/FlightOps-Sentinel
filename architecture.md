# Architecture: FlightOps Sentinel

## 1. Purpose and Scope

FlightOps Sentinel is a production-oriented ML platform that predicts whether a scheduled flight will depart at least 15 minutes late. The MVP serves one binary-classification use case at a fixed prediction horizon of 24 hours before scheduled departure (T-24h).

The architecture is deliberately split into two concerns:

- **data and model lifecycle:** validate data, build features, train, evaluate, register, and batch-score;
- **online serving lifecycle:** expose the approved model through a reliable HTTP API.

Passenger-impact scoring, automated interventions, streaming ingestion, and additional models are explicitly out of scope for this first architecture.

## 2. Logical Architecture

```text
                    ┌───────────────────────────────────────────────┐
                    │                    GitHub                     │
                    │ source code · pull requests · Actions · image  │
                    │              registry / GHCR                   │
                    └───────────────────────┬───────────────────────┘
                                            │ CI/CD
                                            ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                Kubernetes cluster                                  │
│                                                                                   │
│  ┌─────────────────────┐       ┌───────────────────────┐                          │
│  │ Airflow             │       │ MLflow                │                          │
│  │ scheduler/webserver │──────►│ tracking + registry    │                          │
│  │ workers             │       │ metadata + artifacts   │                          │
│  └─────────┬───────────┘       └───────────┬───────────┘                          │
│            │                               │                                      │
│            ▼                               ▼                                      │
│  ┌──────────────────────────────────────────────────┐     ┌───────────────────┐  │
│  │ training / batch-scoring Kubernetes Jobs          │     │ FastAPI service   │  │
│  │ SQL features · train · evaluate · register · score│────►│ /v1/predictions  │  │
│  └─────────────────────┬────────────────────────────┘     └─────────┬─────────┘  │
│                        │                                            │            │
│                        ▼                                            ▼            │
│                 ┌─────────────────┐                       ┌──────────────────┐  │
│                 │ PostgreSQL      │                       │ Ingress          │  │
│                 │ source + ML data│                       │ TLS / routing    │  │
│                 └─────────────────┘                       └──────────────────┘  │
│                                                                                   │
│  ┌────────────────────────┐             ┌─────────────────────────────────────┐ │
│  │ Prometheus + Alertmgr  │◄────────────│ metrics / logs / health endpoints   │ │
│  └───────────┬────────────┘             └─────────────────────────────────────┘ │
│              ▼                                                                    │
│        ┌────────────┐                                                              │
│        │ Grafana    │                                                              │
│        └────────────┘                                                              │
└───────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Environments

| Environment | Purpose | Infrastructure |
| --- | --- | --- |
| Local | Develop, test, and debug individual components. | Docker Compose, local PostgreSQL, local MLflow, local Airflow. |
| CI | Run repeatable checks on every pull request and build immutable images. | GitHub Actions. |
| Staging | Validate a deployable release and end-to-end workflow using non-production data/configuration. | Kubernetes namespace `staging`. |
| Production | Run approved scheduled pipelines and serve API traffic. | Kubernetes namespace `production`; managed PostgreSQL/object storage preferred. |

Local Docker Compose is for developer parity, not the production deployment method. Kubernetes is the production reference runtime.

## 4. Repository and Git Strategy

Git is the source of truth for application code, SQL transformations, Airflow DAGs, infrastructure manifests, model configuration, and documentation. Data, secrets, trained-model binaries, and generated artifacts are not committed to Git.

Suggested branch policy:

- `main` is protected and always deployable.
- Work happens on short-lived feature branches.
- Pull requests require CI success before merge.
- Release images use an immutable Git commit SHA tag; semantic release tags may be added later.

## 5. Application Components

| Component | Runtime | Responsibility |
| --- | --- | --- |
| PostgreSQL | Managed service in production; container locally | Stores operational source data, project-owned derived data, and prediction records. |
| Airflow | Kubernetes deployment | Schedules and monitors data quality, feature materialization, training, evaluation, registration, and batch scoring. |
| Training package | Kubernetes Job launched by Airflow | Extracts versioned training data, trains models, evaluates them, and logs runs to MLflow. |
| Batch-scoring package | Kubernetes Job launched by Airflow | Scores eligible T-24h flights and persists scores. |
| MLflow | Kubernetes deployment + persistent backing services | Tracks experiments, parameters, metrics, model artifacts, and model registry stages. |
| FastAPI prediction service | Kubernetes Deployment | Serves validated, on-demand delay-risk predictions from the approved model. |
| Ingress | Kubernetes Ingress controller | Routes external traffic to FastAPI and terminates TLS. |
| Prometheus | Kubernetes deployment / managed service | Scrapes application, API, and cluster metrics. |
| Grafana | Kubernetes deployment / managed service | Displays operational, data, model, and infrastructure dashboards. |
| Alertmanager | Prometheus companion | Routes actionable alerts to the configured notification channel. |

## 6. Repository Structure

The repository keeps application code, SQL, deployment manifests, tests, and documentation separate. Generated data, MLflow artifacts, local database volumes, virtual environments, and secrets are ignored by Git.

```text
.
├── AGENTS.md
├── README.md
├── prd.md
├── architecture.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Lint, tests, SQL/API contract checks, scans
│       ├── build-publish.yml      # Build and publish immutable container images
│       └── deploy.yml             # Staging deploy, smoke test, production promotion
├── airflow/
│   ├── dags/
│   │   ├── validate_source_data.py
│   │   ├── materialize_features.py
│   │   ├── train_delay_model.py
│   │   ├── batch_score_flights.py
│   │   └── monitor_model_outcomes.py
│   └── Dockerfile
├── src/
│   └── flightops/
│       ├── api/                   # FastAPI routes, schemas, dependencies
│       ├── data/                  # Database connections and data-contract checks
│       ├── features/              # Feature query execution and feature contract
│       ├── training/              # Dataset creation, models, evaluation, MLflow logging
│       ├── scoring/               # Batch and online scoring logic
│       ├── monitoring/            # Metrics, model monitoring, structured logging
│       └── settings.py            # Explicit configuration loading
├── sql/
│   ├── migrations/                # Versioned project-owned schema changes
│   ├── staging/                   # Source projections and cleaning SQL
│   ├── analytics/                 # Historical aggregate SQL
│   ├── ml/                        # Feature and prediction-table SQL
│   └── checks/                    # Data-quality queries
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── fixtures/
├── deploy/
│   ├── helm/                      # Chart or application manifests
│   │   └── flightops/
│   └── environments/
│       ├── staging/
│       └── production/
├── scripts/                       # Explicit developer/admin commands only
└── docs/
    ├── runbooks/
    └── decisions/
```

### Repository conventions

- `src/` contains reusable Python code; Airflow DAG files remain thin orchestration definitions.
- `sql/` contains reviewed, named SQL transformations rather than large inline SQL strings in Python.
- `deploy/` contains declarative Kubernetes configuration only; no credentials are stored there.
- `tests/contract/` checks that API inputs/outputs, feature fields, and model prediction outputs remain compatible with the documented contract.
- `docs/decisions/` stores concise Architecture Decision Records (ADRs) when a non-trivial technical decision is made.

## 7. Component Breakdown

| Component | Code location | Inputs | Outputs | Responsibility | Depends on |
| --- | --- | --- | --- | --- | --- |
| Source validator | `airflow/dags/validate_source_data.py`, `sql/checks/` | `bookings` source tables | `ml.data_quality_results`, Airflow task state | Verify source freshness, schema, nulls, duplicates, and timestamp integrity. | PostgreSQL, Airflow |
| Feature pipeline | `airflow/dags/materialize_features.py`, `sql/staging/`, `sql/analytics/`, `sql/ml/` | Valid source tables | `staging`, `analytics`, `ml.flight_delay_features` | Materialize cutoff-safe, reproducible feature data. | PostgreSQL, Airflow |
| Training job | `src/flightops/training/` | Feature snapshot and train configuration | MLflow run, metrics, model artifact, registry candidate | Chronological split, train, evaluate, calibrate, and register candidate model. | PostgreSQL, MLflow |
| Batch scorer | `src/flightops/scoring/`, `airflow/dags/batch_score_flights.py` | Approved model and eligible feature rows | `ml.flight_delay_predictions` | Score all eligible upcoming flights idempotently. | PostgreSQL, MLflow, Airflow |
| Prediction API | `src/flightops/api/` | `flight_id`, approved model, cutoff-safe features | JSON prediction response, metrics, logs | Serve on-demand validated prediction requests. | PostgreSQL, MLflow |
| MLflow server | Deployment manifest under `deploy/` | Training runs and artifacts | Experiment history and registered model versions | Provide traceability and controlled model promotion. | Persistent metadata DB and artifact storage |
| Monitoring package | `src/flightops/monitoring/` | Pipeline/API/model signals | Prometheus metrics and structured logs | Emit application health, data, and model observability signals. | Prometheus client, logging backend |
| CI/CD workflows | `.github/workflows/` | Git commit, tests, container definitions, deployment config | Test results, immutable images, deployment release | Validate, build, scan, publish, and deploy reviewed changes. | GitHub Actions, container registry, Kubernetes |
| Kubernetes manifests | `deploy/` | Immutable image tags and non-secret configuration | Running workloads, services, ingress, policy | Declare the desired runtime state for each environment. | Kubernetes, image registry, secret store |

### Component interaction rules

1. Only controlled pipelines write to `staging`, `analytics`, and `ml` schemas.
2. FastAPI and batch scoring share one feature contract and one model-loading implementation; they must not implement divergent feature logic.
3. Airflow orchestrates work but does not contain model-training business logic.
4. The API never trains or promotes a model.
5. MLflow records model lineage but does not replace PostgreSQL as the prediction or feature store.
6. Prometheus gathers metrics; it is not a source of business or training data.

## 8. Data Architecture

### 8.1 Source and owned schemas

| Schema | Owner | Access | Purpose |
| --- | --- | --- | --- |
| `bookings` | Airline Demo Database | Read-only for project services | Source airline, booking, ticket, route, airport, aircraft, and flight data. |
| `staging` | FlightOps Sentinel | Read/write through controlled jobs | Typed, cleaned, validated projections of source records. |
| `analytics` | FlightOps Sentinel | Read/write through controlled jobs | Historical aggregates used for analysis and features. |
| `ml` | FlightOps Sentinel | Read/write through controlled jobs | Feature mart, training snapshots, model references, and predictions. |

The system never mutates the source `bookings` schema.

### 8.2 Key project tables

| Table | Grain | Purpose |
| --- | --- | --- |
| `ml.flight_delay_features` | One flight at one prediction cutoff | Reproducible feature row and delayed/not-delayed label for offline training. |
| `ml.training_runs` | One training execution | Links feature snapshot, MLflow run, evaluation metrics, and selected model version. |
| `ml.flight_delay_predictions` | One scored flight | Stores probability, risk level, model version, and score timestamp. |
| `ml.data_quality_results` | One validation check execution | Stores data-contract result, metric, status, and execution metadata. |

### 8.3 Data lineage

```text
bookings.flights + related source tables
          │
          ▼
staging.flight_records
          │
          ▼
analytics.flight_delay_history
          │
          ▼
ml.flight_delay_features
     ┌────┴─────────────────────┐
     ▼                          ▼
training snapshot          scoring feature set
     ▼                          ▼
MLflow run / registry      ml.flight_delay_predictions
```

## 9. Time and Feature Contract

The MVP prediction cutoff is fixed:

```text
feature_cutoff = scheduled_departure - 24 hours
label = actual_departure > scheduled_departure + 15 minutes
```

Each feature must be computable using data available at or before `feature_cutoff`. Historical aggregates exclude the target flight and all subsequent flights. This constraint applies equally to offline training, batch scoring, and the FastAPI service.

Allowed initial features include scheduled departure hour/day/month, origin, destination, route, aircraft type, scheduled duration, and cutoff-safe historical delay aggregates. Actual departure, actual arrival, final status, and all information arriving after cutoff are prohibited from model features.

All timestamps must be timezone-aware. Database and Python time zones are explicitly configured and tested.

## 10. Airflow Workflows

| DAG | Schedule | Main tasks |
| --- | --- | --- |
| `validate_source_data` | Daily / before dependent jobs | Row counts, nulls, duplicates, timestamp ordering, and schema checks. |
| `materialize_features` | Daily | Build staging/analytics tables and the cutoff-safe feature mart. |
| `train_delay_model` | Manual initially; scheduled later | Create chronological split, train baseline/candidate models, evaluate, and log to MLflow. |
| `batch_score_flights` | Daily or more frequently once justified | Select T-24h-eligible flights, score with approved model, and persist predictions. |
| `monitor_model_outcomes` | Daily after labels mature | Compare delayed labels with predictions and calculate model-monitoring metrics. |

Each DAG is idempotent for an execution date. Backfills use an explicit date range and do not silently overwrite historical model results.

## 11. Model Lifecycle and MLflow

1. Airflow starts a training job with a specified feature dataset version/date range.
2. The job uses a chronological train/validation/test split.
3. Parameters, metrics, feature query/version, data snapshot reference, plots, and serialized model are logged to MLflow.
4. A candidate model is registered only when it meets the documented evaluation criteria.
5. Promotion to `Production` is an explicit, reviewable action; the serving service deploys a specific immutable model version.
6. Batch and online predictions record the model version used.

The first baseline should be an interpretable classifier. A more complex model is considered only if it provides a measured benefit on the future holdout data.

## 12. FastAPI Serving Design

### Endpoint

```text
POST /v1/predictions/flight-delay
```

The request contains `flight_id`. The service obtains cutoff-safe features using the same feature definition as offline training, then returns:

```json
{
  "flight_id": 12345,
  "prediction_timestamp": "2026-08-10T10:00:00Z",
  "delay_risk_probability": 0.78,
  "risk_level": "high",
  "model_name": "flight-delay-risk",
  "model_version": "7"
}
```

The service rejects invalid IDs and flights not eligible for T-24h prediction. It does not invent fallback predictions.

### Kubernetes runtime

- Deployment with at least two replicas in production when traffic justifies it.
- Readiness endpoint confirms the service has loaded its configured model and can access required dependencies.
- Liveness endpoint confirms the process is responsive.
- Requests and errors are logged in structured JSON without sensitive passenger data.
- CPU and memory requests/limits are explicit.
- Horizontal Pod Autoscaler can be added when a measured load requirement exists.

## 13. Container and Kubernetes Design

### Container images

Each deployable unit has a small, explicit image:

- `api`: FastAPI application and inference dependencies;
- `pipeline`: feature, training, and scoring packages used by Airflow-launched jobs;
- `airflow`: DAGs and Airflow dependencies.

Images are built once by CI and promoted by immutable SHA tag. The same image is used in staging and production.

### Kubernetes resources

| Workload | Kubernetes resource |
| --- | --- |
| Prediction API | `Deployment` + `Service` + `Ingress` |
| Model training | `Job` initiated by Airflow |
| Batch scoring | `Job` initiated by Airflow |
| Airflow scheduler/webserver/workers | Helm chart deployment or explicit `Deployment` resources |
| MLflow tracking server | `Deployment` + `Service` |
| Scheduled lightweight maintenance | `CronJob`, only where Airflow is not the owner |
| Configuration | `ConfigMap` |
| Secrets | Kubernetes `Secret` backed by a managed secret store in production |

Namespaces isolate environments: `flightops-staging`, `flightops-production`, and optionally `monitoring`.

## 14. CI/CD with GitHub Actions

### Pull-request CI

Every pull request runs:

1. Python formatting and linting.
2. Unit tests.
3. SQL syntax/contract tests.
4. API contract tests.
5. Container image build verification.
6. Dependency and container vulnerability scanning.

No deployment occurs from an unmerged pull request.

### Main branch delivery

On merge to `main`:

1. Build each container image.
2. Tag image with the commit SHA.
3. Push image to GitHub Container Registry or another approved registry.
4. Deploy the immutable image tag to staging.
5. Run smoke tests against staging: API health, database connectivity, and one controlled prediction.
6. Promote the same image to production after the defined approval gate.

Deployments should use Helm or Kustomize manifests stored in Git. CI/CD changes the image tag; it does not make unreviewable infrastructure changes by hand.

## 15. Observability

### Metrics and dashboards

Prometheus scrapes `/metrics` endpoints from FastAPI, Airflow exporters where applicable, MLflow infrastructure, and Kubernetes components. Grafana dashboards include:

| Dashboard | Key signals |
| --- | --- |
| API service | request rate, p50/p95 latency, error rate, pod restarts, model-version request share. |
| Airflow pipelines | DAG success rate, task duration, task failures, schedule delay, feature freshness. |
| Data quality | source row counts, null rate, duplicates, rejected rows, feature-mart freshness. |
| Model quality | delayed-label rate, probability distribution, precision/recall when labels mature, calibration. |
| Infrastructure | CPU, memory, disk, database connections, Kubernetes pod health. |

### Alerts

Initial alerts should be limited to actionable conditions:

- production API unavailable or sustained elevated 5xx rate;
- failed or overdue feature/scoring workflow;
- stale predictions beyond a defined freshness threshold;
- data-quality check failure;
- database connection exhaustion;
- material feature-distribution shift or model-performance degradation once sufficient labelled outcomes exist.

Alertmanager handles routing and deduplication. Notification-channel selection is environment-specific.

### Logging and tracing

- Application logs are structured JSON with request/run correlation IDs.
- Airflow task logs link to DAG run and task IDs.
- Model inference logs include model version and non-sensitive feature/prediction metadata.
- Distributed tracing is a later enhancement; OpenTelemetry-compatible instrumentation should be preferred when added.

## 16. Security and Access Control

- No secrets, credentials, connection strings, or production data are committed to Git.
- Configuration is separated from secrets; secrets are injected at runtime.
- Database roles follow least privilege: source read access, project-schema writer, and application read/prediction writer are distinct where practical.
- Kubernetes service accounts are scoped per workload.
- The API uses TLS at ingress; authentication and authorization are required before exposing it outside a trusted internal network.
- Images run as non-root when compatible with the dependency stack and are vulnerability-scanned in CI.
- Passenger-related fields are not included in prediction responses or standard logs.

## 17. Reliability and Recovery

- Airflow tasks retry only transient, explicitly identified failures; retries are not a substitute for correcting data or code defects.
- Database migrations are versioned and applied through the deployment workflow.
- PostgreSQL backups and restore testing are required for production data.
- MLflow metadata and artifact storage require persistent backups.
- Batch predictions are idempotent by `flight_id`, prediction horizon, model version, and prediction-time policy.
- Rollback deploys the previously known-good immutable container image and retains the prior approved model version.

## 18. Deployment Progression

```text
Phase 1  Docker Compose local stack
Phase 2  CI checks + container images via GitHub Actions
Phase 3  Local Kubernetes (kind or minikube) deployment and Prometheus/Grafana
Phase 4  Staging Kubernetes namespace + automated deploy/smoke test
Phase 5  Production Kubernetes deployment with managed backing services
```

Each phase preserves the same component boundaries. The project should only advance to the next phase after the prior phase is reproducible and documented.

## 19. Architecture Decisions

| Decision | Rationale |
| --- | --- |
| PostgreSQL is the initial data store | The source is already PostgreSQL and relational SQL is central to the project. |
| Batch-first pipeline | The dataset is historical and the MVP does not need streaming infrastructure. |
| Fixed T-24h horizon | Makes feature availability and leakage controls unambiguous. |
| One model only | Keeps focus on a complete, reliable model lifecycle. |
| MLflow registry | Provides traceable experiment-to-model promotion. |
| Kubernetes as production reference | Demonstrates deployment, scaling, and workload isolation without making local development unnecessarily heavy. |
| GitHub Actions CI/CD | Provides auditable automated test, build, scan, and deploy workflow close to the Git repository. |
| Prometheus + Grafana | Provides portable metrics collection and operational visibility across API, jobs, and cluster. |
