# Local Platform Runbook

## Start

Copy `.env.example` to `.env` and supply local secrets. Start the platform after the DemoDB restore, migrations, and feature refresh are complete:

```powershell
docker compose up -d --build postgres minio minio-init mlflow api
docker compose up -d --build airflow-init airflow-webserver airflow-scheduler
docker compose ps
```

The `api` container reads `flight-delay-risk@champion` from MLflow. It remains not-ready until that alias exists.

## Run Orchestration and Batch Scoring

Open Airflow at `http://localhost:8080` and sign in with `AIRFLOW_ADMIN_USERNAME` and `AIRFLOW_ADMIN_PASSWORD` from `.env`, then trigger `validate_source_data`, `materialize_features`, and `batch_score_flights` as appropriate. The batch DAG uses Airflow's data interval and writes predictions idempotently.

For a one-off training job, use the pipeline image:

```powershell
docker compose --profile jobs run --rm pipeline
```

## Smoke Test

With the local API running, execute:

```powershell
.\scripts\smoke-test.ps1
```

The script verifies MLflow and API health, source/feature row availability, champion-model loading, and an API prediction for a currently T-24h eligible flight.

## Stop

```powershell
docker compose down
```

This preserves PostgreSQL and MinIO volumes. Use `docker compose down -v` only when intentionally deleting local service data.

## Troubleshooting

- If API readiness returns `503`, create or restore the MLflow `champion` alias.
- If no flight is eligible for the API smoke test, wait for the next T-24h window or use the API contract test with a controlled clock.
- If Airflow's image build is interrupted by Docker Desktop, restart Docker Desktop and rerun the two `docker compose up` commands above; build layers are cached.
