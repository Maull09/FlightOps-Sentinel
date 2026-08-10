# Product Requirements Document: FlightOps Sentinel

## 1. Product Summary

FlightOps Sentinel is an internal ML service that predicts the risk of departure delay for scheduled flights. It helps operations users identify flights likely to depart 15 minutes or more behind schedule before departure.

The initial release has one ML use case and one prediction unit: a scheduled flight.

## 2. Problem Statement

Operations teams need a consistent, early signal to focus attention on flights that may be delayed. The source operational database contains historical scheduled and actual flight times, but it does not provide a predictive delay-risk score.

Without a risk score, prioritization is manual and reactive.

## 3. Goal

For each eligible scheduled flight, provide a probability that its actual departure will be at least 15 minutes later than its scheduled departure.

```text
is_departure_delayed_15m =
actual_departure > scheduled_departure + 15 minutes
```

## 4. Primary User and Decision

**Primary user:** flight operations analyst or operations service.

**Decision supported:** which upcoming flights should receive closer operational attention because they have elevated delay risk.

## 5. MVP Scope

### In scope

- PostgreSQL Airline Demo Database as the operational source.
- Feature mart derived from historical flight records.
- Binary-classification model for departure delay of 15 minutes or more.
- Time-based training, validation, and test evaluation.
- MLflow experiment tracking and model registry.
- Airflow workflows for data validation, feature creation, training, and batch scoring.
- FastAPI endpoint that returns a flight delay-risk prediction.
- Basic service, pipeline, data-quality, and model-performance monitoring.

### Out of scope

- Arrival-delay, cancellation, missed-connection, and passenger-impact models.
- LLM features or chat interfaces.
- Automated rebooking, notifications, or external ticketing integrations.
- Real-time streaming ingestion.
- A full operations dashboard.

## 6. Data

The source is the PostgreSQL Airline Demo Database in the `bookings` schema. Relevant entities include flights, routes, airports, aircraft, bookings, tickets, segments, and boarding passes.

Project-owned derived schemas will hold staging, analytics, and ML data. The source `bookings` schema is read-only from the project perspective.

## 7. Prediction Contract

### Input

- `flight_id`
- Prediction timestamp / configured prediction horizon

### Output

- `flight_id`
- `prediction_timestamp`
- `delay_risk_probability` between 0 and 1
- `risk_level`: `low`, `medium`, or `high`
- `model_version`

### Initial prediction horizon

The first release predicts at **24 hours before scheduled departure (T-24h)**. This is fixed for the MVP so feature availability and training labels are unambiguous.

## 8. Feature Rules

Permitted features must be available by T-24h, for example:

- scheduled departure time, weekday, month, and hour bucket;
- origin and destination airport;
- route;
- aircraft code/type;
- scheduled duration;
- historical delay aggregates calculated only from flights completed before the feature cutoff.

Prohibited features include actual departure, actual arrival, final flight status, and any information created after the T-24h cutoff.

## 9. Success Metrics

### Model metrics

- ROC-AUC and PR-AUC on a held-out, future time window.
- Recall and precision at the selected high-risk threshold.
- Probability calibration.

### System metrics

- Successful scheduled pipeline runs.
- Freshness of the feature mart and batch predictions.
- API availability and prediction latency.

## 10. Acceptance Criteria

- The source database can be restored and queried locally.
- A reproducible SQL feature dataset is created without target leakage.
- Training runs are tracked in MLflow and a selected model is registered.
- The API produces a valid prediction for an eligible flight.
- Airflow can run the end-to-end batch workflow.
- Documentation explains the target, cutoff time, features, evaluation split, and how to run the system.

## 11. Risks and Decisions

- Historical data is a snapshot, so the MVP will use offline replay/backtesting rather than claim true real-time prediction.
- Data volume may make repeated full-table transformations expensive; pipelines should be incremental where this improves clarity and reliability.
- A model that scores well but uses post-cutoff information is invalid. Leakage prevention takes priority over headline accuracy.
