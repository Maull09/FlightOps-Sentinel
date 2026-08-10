# Implementation Roadmap: FlightOps Sentinel

## How to Use This Roadmap

- Complete phases in order. Do not introduce later infrastructure before the current phase is reproducible.
- Keep the MVP to one model: departure delay risk at the T-24h prediction horizon.
- Mark a task complete only after its verification item passes.
- Update `prd.md` and `architecture.md` when an implementation decision materially changes the documented design.

## Phase 0 — Project Foundation

**Outcome:** a clean, reproducible repository with explicit local configuration.

- [ ] Review `prd.md`, `architecture.md`, and `AGENTS.md`; record any agreed design changes before coding.
- [ ] Create Python project metadata and lock dependency versions.
- [ ] Add `.gitignore` for Python caches, environment files, data volumes, MLflow artifacts, and local secrets.
- [ ] Add `.env.example` with non-secret variable names for PostgreSQL, Airflow, MLflow, and API configuration.
- [ ] Create the initial repository folders defined in `architecture.md`.
- [ ] Add a concise `README.md` with project purpose, prerequisites, local setup outline, and documentation links.
- [ ] Establish formatting, linting, type-checking, and test commands.

**Verify:** a fresh clone can install dependencies, run quality checks, and start with no committed secrets or generated artifacts.

## Phase 1 — Local Infrastructure and Source Database

**Outcome:** the airline demo database is available locally as a reproducible PostgreSQL service.

- [ ] Create Docker Compose services for PostgreSQL, MLflow, and an object/artifact-store dependency if selected.
- [ ] Pin image versions and provide persistent named volumes for local development.
- [ ] Obtain the approved PostgreSQL Airline Demo Database SQL dump and document its source/version.
- [ ] Add an explicit restore command or one-time initialization workflow; never automatically delete an existing database.
- [ ] Create a restricted project database role with read-only access to `bookings` and controlled write access to project-owned schemas.
- [ ] Inspect and document the source schema, table sizes, timestamp columns, flight statuses, and time-zone behavior.
- [ ] Confirm source schema is not mutated by project jobs.

**Verify:** PostgreSQL starts through Docker Compose; the source database restores successfully; a read-only query reaches relevant `bookings` tables.

## Phase 2 — Data Contract and SQL Foundation

**Outcome:** source data is understood, validated, and transformed into project-owned schemas.

- [ ] Define the target label precisely: `actual_departure > scheduled_departure + 15 minutes`.
- [ ] Define T-24h cutoff exactly and document all timestamp assumptions.
- [ ] Write SQL migrations for `staging`, `analytics`, and `ml` schemas.
- [ ] Implement source-data quality checks: schema presence, row counts, nulls, duplicate flight identifiers, timestamp ordering, and valid flight status values.
- [ ] Implement `staging.flight_records` with typed, named fields required by the project.
- [ ] Build a data dictionary for source and derived fields.
- [ ] Add SQL tests for label correctness and invalid timestamp combinations.
- [ ] Decide and document data-refresh assumptions for the static demo-database snapshot.

**Verify:** all data-quality checks run against the restored database; derived tables can be recreated from scratch; the target label is auditable with example rows.

## Phase 3 — Feature Mart and Leakage Controls

**Outcome:** a reproducible, cutoff-safe training and scoring dataset exists in PostgreSQL.

- [ ] Define the prediction grain: one scheduled flight at T-24h.
- [ ] Implement scheduled-time features: hour bucket, day of week, month, route, origin, destination, aircraft, and scheduled duration.
- [ ] Implement historical delay aggregates using only flights completed before each row's cutoff.
- [ ] Explicitly exclude post-cutoff fields such as actual times and final status from feature inputs.
- [ ] Materialize `ml.flight_delay_features` with feature columns, label, scheduled departure, and feature cutoff.
- [ ] Create feature-contract tests for required columns, types, non-null expectations, and cutoff safety.
- [ ] Perform a manual leakage audit on sampled rows and record the result.
- [ ] Decide whether the source data has sufficient historical coverage for each aggregate; omit features that cannot be computed safely.

**Verify:** a feature row can be explained from source records available by its cutoff; all feature-contract tests pass; target leakage is absent by design and sampling review.

## Phase 4 — Baseline Model and Evaluation

**Outcome:** an interpretable, reproducible baseline establishes whether the problem is learnable.

- [ ] Create training code that reads a versioned feature snapshot from PostgreSQL.
- [ ] Implement chronological train, validation, and test splits; do not use random splitting.
- [ ] Train an interpretable baseline binary classifier.
- [ ] Calculate ROC-AUC, PR-AUC, precision, recall, confusion matrix, and calibration metrics on the future test set.
- [ ] Select initial risk thresholds for `low`, `medium`, and `high` with a documented business rationale.
- [ ] Generate evaluation artifacts: metrics report, feature importance/coefficient view where applicable, and calibration plot.
- [ ] Compare against a simple non-ML baseline, such as historical route delay rate.
- [ ] Document limitations caused by the historical snapshot and unavailable external features.

**Verify:** one command produces the same split logic and a tracked evaluation report; the selected model has a justified comparison against the non-ML baseline.

## Phase 5 — MLflow Experiment Tracking and Registry

**Outcome:** every model is traceable to code, data, parameters, metrics, and artifact.

- [ ] Configure MLflow tracking server and persistent backend/artifact storage for local development.
- [ ] Log training parameters, data snapshot identifier, feature definition version, metrics, plots, and serialized model.
- [ ] Register the selected baseline model as `flight-delay-risk`.
- [ ] Define model stages/aliases and explicit promotion criteria.
- [ ] Create `ml.training_runs` and record links to MLflow run and registered model version.
- [ ] Add a reproducibility test that loads a registered model and produces a prediction from a known feature fixture.

**Verify:** an MLflow run can be opened from its recorded identifier; the registered model loads successfully; prediction records identify the exact model version.

## Phase 6 — Airflow Orchestration and Batch Scoring

**Outcome:** the offline ML workflow is scheduled, observable, and idempotent.

- [ ] Add Airflow to Docker Compose.
- [ ] Implement thin DAGs: `validate_source_data`, `materialize_features`, `train_delay_model`, `batch_score_flights`, and `monitor_model_outcomes`.
- [ ] Move reusable business logic into `src/`; keep DAG files focused on dependency ordering and configuration.
- [ ] Implement task-level logging and retry behavior only for identified transient failures.
- [ ] Implement batch scoring for eligible T-24h flights using the approved registered model.
- [ ] Write scores to `ml.flight_delay_predictions` with model version and prediction timestamp.
- [ ] Enforce idempotency for the defined prediction uniqueness key.
- [ ] Test DAGs locally, including one intentionally failed data-quality task.

**Verify:** a manual end-to-end DAG run validates data, materializes features, and writes batch predictions; rerunning the same logical execution does not create duplicate predictions.

## Phase 7 — FastAPI Prediction Service

**Outcome:** an internal service returns consistent, validated on-demand predictions.

- [ ] Implement settings and configuration loading with environment variables.
- [ ] Implement `POST /v1/predictions/flight-delay`.
- [ ] Validate `flight_id` and T-24h eligibility.
- [ ] Reuse the shared feature contract and model-loading implementation; do not duplicate feature logic.
- [ ] Return probability, risk level, prediction timestamp, model name, and model version.
- [ ] Implement `/health/live`, `/health/ready`, and `/metrics` endpoints.
- [ ] Add unit tests, API contract tests, and integration tests against local PostgreSQL/MLflow.
- [ ] Add structured JSON logging with request correlation IDs and no sensitive passenger attributes.

**Verify:** the API returns a valid prediction for a known eligible flight; invalid and ineligible requests receive clear errors; API output agrees with the equivalent batch-scoring result.

## Phase 8 — Dockerization and Local End-to-End Validation

**Outcome:** the full local platform runs from documented commands.

- [ ] Create separate Dockerfiles for API, pipeline job, and Airflow environment.
- [ ] Ensure images run with explicit configuration and no embedded credentials.
- [ ] Add health checks and named networks/volumes to Docker Compose.
- [ ] Write a local smoke-test script: infrastructure health, source connection, feature query, MLflow model load, and API prediction.
- [ ] Document startup, shutdown, data restore, DAG execution, and troubleshooting steps.
- [ ] Validate a clean-machine workflow using only repository documentation.

**Verify:** after a clean setup, a developer can restore the data, start services, run a DAG, and call the API without manual code changes.

## Phase 9 — Observability

**Outcome:** operators can detect service, pipeline, data, and model problems.

- [ ] Add Prometheus metrics to FastAPI: request count, latency, error count, loaded model version, and prediction count.
- [ ] Deploy Prometheus, Grafana, and Alertmanager locally or in the first Kubernetes environment.
- [ ] Build an API-service Grafana dashboard.
- [ ] Build an Airflow/pipeline dashboard covering task status and feature/prediction freshness.
- [ ] Emit and visualize data-quality metrics.
- [ ] Add model-monitoring jobs for label rate, score distribution, feature distributions, and delayed performance metrics when labels mature.
- [ ] Define a small set of actionable alerts and test at least one alert route.
- [ ] Write operational runbooks for failed pipeline, stale predictions, unavailable API, and model rollback.

**Verify:** dashboards display live signals; a simulated pipeline/API failure creates an observable alert; each alert has a documented response.

## Phase 10 — CI/CD with GitHub Actions

**Outcome:** changes are automatically validated, packaged, and safely promoted.

- [ ] Add pull-request workflow for formatting, linting, unit tests, SQL tests, API contract tests, and dependency checks.
- [ ] Add container build and vulnerability-scanning workflow.
- [ ] Publish immutable SHA-tagged images to the selected registry after merge to `main`.
- [ ] Add Kubernetes manifest/chart validation in CI.
- [ ] Add staging deployment workflow using the immutable image tag.
- [ ] Add post-deployment smoke tests: API readiness, database connectivity, and controlled prediction.
- [ ] Define the manual approval gate for production promotion.
- [ ] Protect `main` with required status checks and review policy.

**Verify:** a pull request cannot merge with failed checks; a merge produces immutable images and a successful staging smoke test.

## Phase 11 — Kubernetes Deployment

**Outcome:** the system runs in a Kubernetes environment with explicit resource and security configuration.

- [ ] Start with local Kubernetes using kind or minikube.
- [ ] Create namespace, ConfigMap, Secret references, ServiceAccounts, and resource requests/limits.
- [ ] Deploy FastAPI as Deployment + Service + Ingress with readiness and liveness probes.
- [ ] Deploy MLflow and Airflow with persistent backing services/storage appropriate to the environment.
- [ ] Configure Airflow to launch training and scoring Kubernetes Jobs.
- [ ] Deploy Prometheus/Grafana/Alertmanager or connect managed equivalents.
- [ ] Validate rolling API deployment and rollback to a prior immutable image.
- [ ] Create staging and production overlays/values with no hard-coded secrets.

**Verify:** the complete platform runs in local Kubernetes; the API is reachable through ingress; batch workflow executes as Kubernetes Jobs; rollback is demonstrated.

## Phase 12 — Production Readiness and Portfolio Handoff

**Outcome:** the project is understandable, demonstrable, and credible as a production-oriented portfolio system.

- [ ] Perform end-to-end acceptance testing against every criterion in `prd.md`.
- [ ] Review access control, secret handling, backups, logging, and recovery runbooks.
- [ ] Verify data/model lineage from a prediction record back to feature dataset, MLflow run, and Git commit.
- [ ] Capture system screenshots or a short demo: Airflow DAG, MLflow experiment, API call, Grafana dashboard, and Kubernetes workloads.
- [ ] Write architecture trade-offs and known limitations.
- [ ] Ensure README describes the business problem, architecture, setup, test strategy, API, monitoring, and future roadmap.
- [ ] Tag a demonstrable release in Git.

**Verify:** another technical reviewer can follow the documentation, reproduce the local deployment, understand the design decisions, and trace a prediction end-to-end.

## Suggested First Implementation Slice

Start with the smallest vertical slice that proves the core idea:

1. PostgreSQL source database restored locally.
2. One SQL query builds a leakage-safe labelled flight dataset.
3. One baseline classifier trains from that dataset and logs to MLflow.
4. One FastAPI endpoint loads the registered model and predicts for one flight.

Only then add Airflow, full observability, CI/CD, and Kubernetes. This order keeps each layer tied to a working product behavior.
