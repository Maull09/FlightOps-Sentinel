# Observability Runbook

## Local Services

Start the observability stack after the API is healthy:

```powershell
docker compose up -d prometheus alertmanager grafana
```

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3300`
- Alertmanager: `http://localhost:9093`

Grafana provisions the `FlightOps API Service` dashboard automatically. The dashboard shows request rate, error rate, p95 latency, and prediction freshness.

## Signals

The API exposes `/metrics` for Prometheus. It includes request/latency/error counts, prediction count by model version, loaded champion version, failed data-contract checks, prediction freshness, and matured delay rate.

Request paths use route templates; unmatched URLs share the label `unmatched`. Unhandled exceptions count as HTTP 500. If there are no predictions or matured labels, freshness/rate gauges emit `NaN` to represent missing observations. These missing observations do not trigger a numeric stale-prediction threshold; investigate an empty prediction history during initial setup. An unavailable champion is logged and reported with version `unavailable`. The model info metric describes the current alias, while prediction counters describe the version actually loaded for inference.

Prometheus evaluates three alerts:

- `FlightOpsApiUnavailable`: API scrape target unavailable for one minute.
- `FlightOpsDataQualityFailure`: a latest data-contract check fails for five minutes.
- `FlightOpsPredictionsStale`: latest prediction is older than 48 hours for 30 minutes.

The local Alertmanager receiver logs alerts only. Production must replace it with an owned notification route.

## Response

- API unavailable: inspect `docker compose logs api`, restore the `champion` alias if readiness fails, then restart `api`.
- Failed pipeline/data quality: inspect Airflow task logs and `ml.data_quality_results`; correct source or transform issues, refresh features, then rerun contracts.
- Stale predictions: inspect `batch_score_flights` in Airflow, verify MLflow champion availability, then rerun the affected data interval. The scoring insert is idempotent.
- Model rollback: point MLflow alias `champion` to the prior eligible registered version, then restart API instances to clear their model load path.

## Test an Alert Route

Stop the API locally, wait one scrape plus one minute, and inspect Prometheus Alerts or Alertmanager. Restart the API afterwards:

```powershell
docker compose stop api
docker compose up -d api
```

## Simulate Production-Like API Traffic

Use the controlled local traffic simulator after the API, PostgreSQL, MLflow, and Prometheus are running:

```powershell
.\.venv\Scripts\python.exe scripts\simulate-production-traffic.py --requests 120 --concurrency 8 --error-rate 0.10
```

It selects only currently T-24h eligible flights, sends concurrent valid requests, and deliberately sends a small proportion of unknown flight IDs to exercise the API error metric. It prints status counts, throughput, and latency percentiles; it does not alter source data or write on-demand prediction rows.

After the run, inspect Prometheus with `http://localhost:9090/graph?g0.expr=flightops_api_requests_total` and the provisioned Grafana API dashboard. A successful simulation should have HTTP `200` responses, expected HTTP `404` responses, no `5xx` responses, and a prediction counter labelled with the champion model version.
