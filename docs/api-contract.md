# Flight Delay Prediction API Contract

## Endpoint

```text
POST /v1/predictions/flight-delay?flight_id={flight_id}
```

The endpoint reads the same cutoff-safe fields from `ml.flight_delay_features` used by batch scoring. A flight is eligible only after its T-24h feature cutoff and before its scheduled departure.

## Successful Response

```json
{
  "flight_id": 12345,
  "prediction_timestamp": "2026-08-11T00:00:00Z",
  "delay_risk_probability": 0.04,
  "risk_level": "medium",
  "model_name": "flight-delay-risk",
  "model_version": "23"
}
```

The API resolves the MLflow alias `champion` once, then loads the exact registry version. The response reports the version actually loaded, including when the alias changes during a request. It never substitutes an unapproved model. Risk bands are `low` below 0.03, `medium` from 0.03 to below 0.06, and `high` from 0.06.

`/health` and `/health/live` report process liveness. `/health/ready` verifies that the champion alias can be resolved; it does not load the artifact or check PostgreSQL connectivity. Use the platform smoke test for those checks.

The app reads runtime environment variables. The local `serve-api.py` entry point loads `.env` before starting Uvicorn; importing the app does not overwrite process configuration.

## Errors

- `404`: the feature mart has no row for the requested flight.
- `400`: the flight is before its T-24h cutoff or has already departed.
- `503`: no model has been explicitly promoted to the `champion` alias, or the approved model cannot be loaded.

## Local Run

```powershell
.\.venv\Scripts\python.exe .\scripts\serve-api.py
Invoke-WebRequest http://localhost:8000/health
```

The local API was verified against `flight-delay-risk@champion` version `23` for eligible flight `55921`, returning HTTP `200`, probability `0.04949`, and risk level `medium`.
