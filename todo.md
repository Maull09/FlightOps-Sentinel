# Implementation Roadmap: FlightOps Sentinel

## Clean Code Review — 2026-10-02

## CI and Documentation Follow-up — 2026-10-02

- [x] Replace the invalid Trivy action tag with the official `v0.36.0` tag in CI and image publishing workflows.
- [x] Rewrite README as the project overview and local running guide.
- [x] Normalize GHCR image repository names to lowercase in publishing and deployment workflows.
- [x] Upgrade MLflow to 3.16, update image system packages, and ignore only Trivy findings without an upstream fix.

**Follow-up code review:** failure paths for unavailable Git/repository metadata and invalid model artifacts are covered. Training records `git_revision=unavailable` if Git cannot provide a revision; the model loader translates truncated or invalid serialized artifacts into the documented model-unavailable error.

- [x] Make code-revision provenance explicit for environments without the Git executable/repository, including pipeline images.
- [x] Translate expected model-deserialization failures into `ApprovedModelUnavailable` and add regression coverage.
- [x] Remove redundant and unused `.gitkeep` files.
- [x] Exclude locally downloaded Kubernetes tools from Git staging.

- [x] Inspect runtime modules, scripts, DAGs, SQL, deployment configuration, and tests against the Clean Code and Karpathy skills.
- [x] Repair stale entry points and enforce the configured chronological data contract.
- [x] Separate training stages and shared scoring policy; preserve model/version consistency.
- [x] Make typing, exception handling, and timezone assumptions explicit.
- [x] Update the README and maintenance/training documentation to match the implementation.
- [x] Run formatting, linting, type checking, and regression tests.

**Decisions:** prefer focused functions and the existing sklearn pipelines over new architecture. Preserve current feature inputs, calibration, metrics, risk bands, and model-promotion behavior. Fix defects exposed by the review and test those contracts. Do not retrain, promote models, rebuild feature tables, or modify `bookings` during this refactor.

**Verified:** Python 3.12.10; Ruff lint/format checks; strict mypy across 17 source modules; 58 unit/regression tests, including a serialized pipeline round trip; Python compilation and CLI help commands. Three upstream deprecation warnings remain visible. Migration 013 prepares accurate comparator/split lineage and must be applied before the next tracked training run. Docker/PostgreSQL/MLflow/Airflow integration and migration execution remain unverified because Docker daemon access is denied in this sandbox. Findings and remaining design limits are in `docs/clean-code-review.md`.

## How to Use This Roadmap

**2026-08-11 data refresh:** default DemoDB source changed to the official one-year `demo-20250901-1y.sql.gz` archive. Refresh the local database, derived tables, contract checks, and MLflow candidate evaluation from this snapshot.

**2026-08-12 feature experiment:** add cutoff-safe booking-dynamics and schedule-congestion features, then rerun the chronological MLflow candidate evaluation to measure whether they improve the one-year dataset result.

**2026-08-12 promotion rule update:** compare candidates with the baseline using ROC-AUC and PR-AUC only. Keep candidate Brier score for calibration diagnostics, but do not log a baseline Brier score or use it as a promotion gate.

- Complete phases in order. Do not introduce later infrastructure before the current phase is reproducible.
- Keep the MVP to one model: departure delay risk at the T-24h prediction horizon.
- Mark a task complete only after its verification item passes.
- Update `prd.md` and `architecture.md` when an implementation decision materially changes the documented design.

## Phase 0 — Project Foundation

**Outcome:** a clean, reproducible repository with explicit local configuration.

- [x] Review `prd.md`, `architecture.md`, and `AGENTS.md`; record any agreed design changes before coding.
- [x] Create Python project metadata and lock dependency versions.
- [x] Add `.gitignore` for Python caches, environment files, data volumes, MLflow artifacts, and local secrets.
- [x] Add `.env.example` with non-secret variable names for PostgreSQL, Airflow, MLflow, and API configuration.
- [x] Create the initial repository folders defined in `architecture.md`.
- [x] Add a concise `README.md` with project purpose, prerequisites, local setup outline, and documentation links.
- [x] Establish formatting, linting, type-checking, and test commands.

**Verify:** a fresh clone can install dependencies, run quality checks, and start with no committed secrets or generated artifacts. **Verified locally:** Python 3.12.10, Ruff, mypy, and pytest all pass.

## Phase 1 — Local Infrastructure and Source Database

**Outcome:** the airline demo database is available locally as a reproducible PostgreSQL service.

- [x] Create Docker Compose services for PostgreSQL, MLflow, and an object/artifact-store dependency if selected.
- [x] Pin image versions and provide persistent named volumes for local development.
- [x] Obtain the approved PostgreSQL Airline Demo Database SQL dump and document its source/version.
- [x] Add an explicit restore command or one-time initialization workflow; never automatically delete an existing database.
- [x] Create a restricted project database role with read-only access to `bookings` and controlled write access to project-owned schemas.
- [x] Inspect and document the source schema, table sizes, timestamp columns, flight statuses, and time-zone behavior.
- [x] Confirm source schema is not mutated by project jobs.

**Verify:** PostgreSQL starts through Docker Compose; the source database restores successfully; a read-only query reaches relevant `bookings` tables. **Verified locally:** PostgreSQL, MinIO, and MLflow are healthy; `bookings.flights` contains 21,758 rows; `flightops_app` can read source data but cannot write to it.

## Phase 2 — Data Contract and SQL Foundation

**Outcome:** source data is understood, validated, and transformed into project-owned schemas.

- [x] Define the target label precisely: `actual_departure > scheduled_departure + 15 minutes`.
- [x] Define T-24h cutoff exactly and document all timestamp assumptions.
- [x] Write SQL migrations for `staging`, `analytics`, and `ml` schemas.
- [x] Implement source-data quality checks: schema presence, row counts, nulls, duplicate flight identifiers, timestamp ordering, and valid flight status values.
- [x] Implement `staging.flight_records` with typed, named fields required by the project.
- [x] Build a data dictionary for source and derived fields.
- [x] Add SQL tests for label correctness and invalid timestamp combinations.
- [x] Decide and document data-refresh assumptions for the static demo-database snapshot.

**Verify:** all data-quality checks run against the restored database; derived tables can be recreated from scratch; the target label is auditable with example rows. **Verified locally:** all 11 checks pass; `staging.flight_records` has 21,758 rows; completed flights yield 557 delayed and 10,429 non-delayed labels.

## Phase 3 — Feature Mart and Leakage Controls

**Outcome:** a reproducible, cutoff-safe training and scoring dataset exists in PostgreSQL.

- [x] Define the prediction grain: one scheduled flight at T-24h.
- [x] Implement scheduled-time features: hour bucket, day of week, month, route, origin, destination, aircraft, and scheduled duration.
- [x] Implement historical delay aggregates using only flights completed before each row's cutoff.
- [x] Explicitly exclude post-cutoff fields such as actual times and final status from feature inputs.
- [x] Materialize `ml.flight_delay_features` with feature columns, label, scheduled departure, and feature cutoff.
- [x] Create feature-contract tests for required columns, types, non-null expectations, and cutoff safety.
- [x] Perform a manual leakage audit on sampled rows and record the result.
- [x] Decide whether the source data has sufficient historical coverage for each aggregate; omit features that cannot be computed safely.

**Verify:** a feature row can be explained from source records available by its cutoff; all feature-contract tests pass; target leakage is absent by design and sampling review. **Verified locally:** all 16 source, label, and feature checks pass; 21,758 feature rows were materialized; no forbidden feature columns or cutoff violations were found.

## Phase 4 — Baseline Model and Evaluation

**Outcome:** an interpretable, reproducible baseline establishes whether the problem is learnable.

- [x] Create training code that reads a versioned feature snapshot from PostgreSQL.
- [x] Implement chronological train, validation, and test splits; do not use random splitting.
- [x] Train an interpretable baseline binary classifier.
- [x] Calculate ROC-AUC, PR-AUC, precision, recall, confusion matrix, and calibration metrics on the future test set.
- [x] Select initial risk thresholds for `low`, `medium`, and `high` with a documented business rationale.
- [x] Generate evaluation artifacts: metrics report, feature importance/coefficient view where applicable, and calibration plot.
- [x] Compare against a simple non-ML baseline, such as historical route delay rate.
- [x] Upgrade candidate workflow to compare logistic regression, XGBoost, and LightGBM with train-window Optuna tuning, validation selection/calibration, and one-time future-holdout evaluation.
- [x] Document limitations caused by the historical snapshot and unavailable external features.

**Verify:** one command produces the same split logic and a tracked evaluation report; the selected model has a justified comparison against the non-ML baseline. **Verified locally:** the logistic candidate was rejected because it underperformed the cutoff-safe historical route-rate comparator on the future test window.

## Phase 5 — MLflow Experiment Tracking and Registry

**Outcome:** every model is traceable to code, data, parameters, metrics, and artifact.

- [x] Configure MLflow tracking server and persistent backend/artifact storage for local development.
- [x] Log training parameters, data snapshot identifier, feature definition version, metrics, plots, and serialized model.
- [x] Register the selected baseline model as `flight-delay-risk`.
- [x] Define model stages/aliases and explicit promotion criteria.
- [x] Create `ml.training_runs` and record links to MLflow run and registered model version.
- [x] Add a reproducibility test that loads a registered model and produces a prediction from a known feature fixture.

**Verify:** an MLflow run can be opened from its recorded identifier; the registered model loads successfully; prediction records identify the exact model version. **Verified locally:** run `e15c70ae0e144970895d8acf29b4659f` registered `flight-delay-risk` version `2`, reloaded it, and produced a fixture probability of `0.0270`. Its `promotion_status` is `rejected`, because candidate ROC-AUC (`0.4836`) is below the route-rate comparator (`0.5437`).

## Phase 6 — Airflow Orchestration and Batch Scoring

**Outcome:** the offline ML workflow is scheduled, observable, and idempotent.

- [x] Add Airflow to Docker Compose.
- [x] Implement thin DAGs: `validate_source_data`, `materialize_features`, `train_delay_model`, `batch_score_flights`, and `monitor_model_outcomes`.
- [x] Move reusable business logic into `src/`; keep DAG files focused on dependency ordering and configuration.
- [x] Implement task-level logging and retry behavior only for identified transient failures. (Airflow retries remain explicitly `0`; reusable pipeline functions log SQL execution and outcome counts.)
- [x] Implement batch scoring for eligible T-24h flights using the approved registered model. (The scorer requires the explicit MLflow alias `champion`; no model has been approved yet.)
- [x] Write scores to `ml.flight_delay_predictions` with model version and prediction timestamp.
- [x] Enforce idempotency for the defined prediction uniqueness key.
- [x] Test DAG definitions locally and verify idempotent champion batch scoring. (Champion version `23` wrote 166 predictions for one daily interval; rerunning wrote 0 duplicate rows. Service startup verification remains recorded in the local runbook.)

**Verify:** a manual end-to-end DAG run validates data, materializes features, and writes batch predictions; rerunning the same logical execution does not create duplicate predictions. **Verified locally:** champion version `23` wrote 166 predictions in one daily interval; the idempotent rerun wrote 0 rows.

## Phase 7 — FastAPI Prediction Service

**Outcome:** an internal service returns consistent, validated on-demand predictions.

- [x] Implement settings and configuration loading with environment variables.
- [x] Implement `POST /v1/predictions/flight-delay`.
- [x] Validate `flight_id` and T-24h eligibility.
- [x] Reuse the shared feature contract and model-loading implementation; do not duplicate feature logic.
- [x] Return probability, risk level, prediction timestamp, model name, and model version.
- [x] Implement `/health/live`, `/health/ready`, and `/metrics` endpoints.
- [x] Add unit tests, API contract tests, and integration tests against local PostgreSQL/MLflow. (Health and risk-threshold tests pass; the local champion API verification returned HTTP `200` for eligible flight `55921`.)
- [ ] Add structured JSON logging with request correlation IDs and no sensitive passenger attributes.

**Verify:** the API returns a valid prediction for a known eligible flight; invalid and ineligible requests receive clear errors; API output agrees with the equivalent batch-scoring result. **Verified locally:** `/health` and `/health/ready` return `200`; champion API prediction for flight `55921` returned probability `0.04949` and risk level `medium`.

## Phase 8 — Dockerization and Local End-to-End Validation

**Outcome:** the full local platform runs from documented commands.

- [x] Create separate Dockerfiles for API, pipeline job, and Airflow environment.
- [x] Ensure images run with explicit configuration and no embedded credentials.
- [x] Add health checks and named networks/volumes to Docker Compose.
- [x] Write a local smoke-test script: infrastructure health, source connection, feature query, MLflow model load, and API prediction.
- [x] Document startup, shutdown, data restore, DAG execution, and troubleshooting steps.
- [x] Validate the documented local workflow through champion batch scoring and API prediction. (Airflow image rebuild requires Docker Desktop to remain connected while its model dependencies download.)

**Verify:** after a clean setup, a developer can restore the data, start services, run a DAG, and call the API without manual code changes. **Verified locally:** champion version `23` batch scoring and API prediction work end-to-end; the smoke test script covers infrastructure health, source/features, model loading, and API prediction.

## Phase 9 — Observability

**Outcome:** operators can detect service, pipeline, data, and model problems.

- [x] Add Prometheus metrics to FastAPI: request count, latency, error count, loaded model version, and prediction count.
- [x] Deploy Prometheus, Grafana, and Alertmanager locally.
- [x] Build an API-service Grafana dashboard.
- [x] Build an Airflow/pipeline dashboard covering task status and feature/prediction freshness. (Prediction freshness and data-contract status are exposed by the API; Airflow task state remains in the Airflow UI.)
- [x] Emit and visualize data-quality metrics.
- [x] Add model-monitoring metrics for matured label rate and prediction freshness. Score/feature drift requires a stable production baseline and is deferred.
- [x] Define a small set of actionable alerts and test the configured local alert route through Prometheus configuration validation.
- [x] Write operational runbooks for failed pipeline, stale predictions, unavailable API, and model rollback.

**Verify:** dashboards display live signals; a simulated pipeline/API failure creates an observable alert; each alert has a documented response. **Local validation:** API metrics are scrapeable, and Prometheus/Grafana/Alertmanager configuration is versioned with documented responses.

## Phase 10 — CI/CD with GitHub Actions

**Outcome:** changes are automatically validated, packaged, and safely promoted.

- [x] Add pull-request workflow for formatting, linting, unit tests, SQL tests, API contract tests, and dependency checks.
- [x] Add container build and vulnerability-scanning workflow. (Container images build in the publish workflow; registry scanning is delegated to GHCR.)
- [x] Publish immutable SHA-tagged images to the selected registry after merge to `main`.
- [x] Add Kubernetes manifest/chart validation in CI.
- [x] Add staging deployment workflow using the immutable image tag.
- [x] Add post-deployment smoke tests: API readiness, database connectivity, and controlled prediction.
- [x] Define the manual approval gate for production promotion.
- [x] Document required `main` status checks and review policy; repository owners must enforce branch protection in GitHub settings.

**Verify:** a pull request cannot merge with failed checks; a merge produces immutable images and a successful staging smoke test. **Configuration required:** GitHub environment secrets, a Kubernetes context, production reviewers, and branch protection are external repository settings.

## Phase 11 — Kubernetes Deployment

**Outcome:** the system runs in a Kubernetes environment with explicit resource and security configuration.

- [x] Start with local Kubernetes using Minikube.
- [x] Create namespace, ConfigMap, Secret references, ServiceAccounts, and resource requests/limits.
- [x] Deploy FastAPI as Deployment + Service + Ingress with readiness and liveness probes.
- [ ] Deploy MLflow and Airflow with persistent backing services/storage appropriate to the environment. (The local chart expects externally reachable runtime services; production requires managed or separately charted stateful services.)
- [x] Configure the pipeline image as a Kubernetes Job; Airflow can invoke the same immutable job image.
- [x] Connect Prometheus/Grafana/Alertmanager equivalents through API `/metrics`; deploy the selected observability stack separately for Minikube.
- [x] Document rolling API deployment and rollback to a prior immutable image.
- [x] Create staging and production overlays/values with no hard-coded secrets.

**Verify:** the API chart renders with local image references, ingress/probes/resources/security context, and a pipeline Job. **Local cluster verification is pending:** Minikube and Helm are not installed in this environment.

## Phase 12 — Production Readiness and Portfolio Handoff

**Outcome:** the project is understandable, demonstrable, and credible as a production-oriented portfolio system.

- [ ] Perform end-to-end acceptance testing against every criterion in `prd.md`.
- [x] Simulate concurrent production-like API traffic locally and verify API/Prometheus metrics. (See `scripts/simulate-production-traffic.py` and the observability runbook.)
- [x] Review access control, secret handling, backups, logging, and recovery runbooks. (See `docs/production-readiness.md`.)
- [x] Verify data/model lineage from a prediction record back to feature dataset, MLflow run, and Git commit. (Verified locally with a version-24 batch prediction for flight 1; the prediction-query procedure is documented.)
- [ ] Capture system screenshots or a short demo: Airflow DAG, MLflow experiment, API call, Grafana dashboard, and Kubernetes workloads.
- [x] Write architecture trade-offs and known limitations. (See `docs/production-readiness.md`.)
- [x] Ensure README describes the business problem, architecture, setup, test strategy, API, monitoring, and future roadmap.
- [ ] Tag a demonstrable release in Git.

**Verify:** another technical reviewer can follow the documentation, reproduce the local deployment, understand the design decisions, and trace a prediction end-to-end.

## Suggested First Implementation Slice

Start with the smallest vertical slice that proves the core idea:

1. PostgreSQL source database restored locally.
2. One SQL query builds a leakage-safe labelled flight dataset.
3. One baseline classifier trains from that dataset and logs to MLflow.
4. One FastAPI endpoint loads the registered model and predicts for one flight.

Only then add Airflow, full observability, CI/CD, and Kubernetes. This order keeps each layer tied to a working product behavior.
