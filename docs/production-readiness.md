# Production Readiness Review

The service evidence below was recorded before the 2026-10-02 refactor. It is not a live availability check. See the [Clean Code review](clean-code-review.md) for current offline verification, required lineage migration, and unresolved runtime/design checks.

## Acceptance Checklist

| PRD criterion | Evidence | Status |
| --- | --- | --- |
| Source restores and is queryable | One-year DemoDB restore runbook; `bookings.flights` contains 69,710 rows. | Verified locally |
| Leakage-safe feature dataset | T-24h feature contract and 18 data checks. | Verified locally |
| Tracked, registered model | MLflow `flight-delay-risk@champion` version 24; run `f1ff6dff24ca4ea8b07e54a5cc81af54` is also stored in `ml.training_runs`. | Verified locally |
| Eligible API prediction | API, container health, and smoke test pass. | Verified locally |
| Production-like API traffic | 120 concurrent requests at concurrency 8: 106 valid `200` predictions, 14 intentional unknown-flight `404` responses, zero `5xx`; Prometheus recorded model version 24 and p95 latency of 2.38 seconds. | Verified locally |
| Airflow batch workflow | DAGs and idempotent batch scorer are present. | Verified locally; DAG task execution needs the local Airflow service |
| Documentation | Runbooks, contracts, observability, CI/CD, and Minikube deployment are versioned. | Verified locally |

## Security and Recovery

- Runtime credentials stay in `.env`, Kubernetes Secrets, or protected GitHub environment secrets; they are never placed in source, Helm values, or images.
- The project role has read-only access to `bookings`; only `staging`, `analytics`, and `ml` are project-owned write targets.
- PostgreSQL and MinIO Docker volumes persist through `docker compose down`. Back up both volumes before destructive maintenance.
- API runs non-root in Kubernetes with a read-only filesystem and no Linux capabilities.
- Recovery sequence: restore source database, apply migrations, refresh staging/features, restore MLflow/MinIO metadata/artifacts, set the approved `champion` alias, then run the smoke test.

## Prediction Lineage

Each prediction contains `model_name` and `model_version`. The current champion's run, registry version, metrics, and promotion eligibility were verified in `ml.training_runs`. A locally persisted version-24 prediction for flight `1` successfully joins to MLflow run `f1ff6dff24ca4ea8b07e54a5cc81af54`. Query any prediction's lineage in PostgreSQL:

```sql
SELECT predictions.flight_id, predictions.model_name, predictions.model_version,
       runs.mlflow_run_id, runs.test_metrics, runs.created_at
FROM ml.flight_delay_predictions AS predictions
JOIN ml.training_runs AS runs
  ON runs.model_name = predictions.model_name
 AND runs.registered_model_version = predictions.model_version
WHERE predictions.flight_id = :flight_id;
```

The MLflow run contains the dataset snapshot, versioned feature config, parameters, registered model artifact, and Git revision. The feature row contains its fixed cutoff and scheduled timestamp.

## Trade-offs and Known Limitations

- DemoDB is an offline snapshot; it does not provide real-time weather, ATC, crew, maintenance, or aircraft-rotation data. These missing signals explain the modest predictive performance.
- Schedule congestion uses a published-schedule assumption because the snapshot has no schedule amendment history. Production must use an as-of schedule feed.
- The model is a decision-support signal, not an automated operational action.
- Minikube chart deploys API and an immutable pipeline Job. Stateful MLflow, Airflow, PostgreSQL, MinIO, and observability dependencies require managed services or separately maintained production charts.

## Portfolio Demo

Capture these five views before a presentation: Airflow DAG list, MLflow champion run, successful API response, Grafana API dashboard, and `kubectl get pods` output. Create a Git release tag only after the target repository's branch protection and environment approvals are configured.

## Local Traffic Simulation Evidence

The controlled simulation at `scripts/simulate-production-traffic.py` exercises the deployed Docker API, PostgreSQL feature lookup, MLflow champion lookup/model load, Prometheus scrape, and Grafana-ready metrics. It does not claim a production capacity benchmark: the local Docker Desktop host, snapshot data, and repeated per-request model loading are deliberately different from a production autoscaled service.
