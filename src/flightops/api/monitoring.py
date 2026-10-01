"""Prometheus instruments and database-backed monitoring values."""

from __future__ import annotations

import logging

import psycopg
from prometheus_client import Counter, Gauge, Histogram, Info

from flightops.database import database_connection_string
from flightops.scoring.model import MODEL_NAME, ApprovedModelUnavailable, approved_model_version

LOGGER = logging.getLogger(__name__)
PREDICTION_REQUESTS = Counter("flightops_prediction_requests_total", "Prediction requests")
API_REQUESTS = Counter(
    "flightops_api_requests_total", "API requests", ["method", "path", "status_code"]
)
API_REQUEST_LATENCY = Histogram(
    "flightops_api_request_duration_seconds", "API request duration", ["method", "path"]
)
API_ERRORS = Counter(
    "flightops_api_errors_total", "API responses with error status", ["status_code"]
)
PREDICTION_COUNT = Counter(
    "flightops_predictions_total", "Successful predictions", ["model_version"]
)
LOADED_MODEL = Info("flightops_loaded_model", "Currently approved model")
DATA_QUALITY_FAILURES = Gauge("flightops_data_quality_failed_checks", "Latest failed data checks")
PREDICTION_FRESHNESS = Gauge(
    "flightops_prediction_freshness_seconds", "Age of the latest prediction"
)
MATURED_LABEL_RATE = Gauge("flightops_matured_delay_rate", "Delay rate among matured predictions")


def refresh_monitoring_metrics() -> None:
    with psycopg.connect(database_connection_string()) as connection:
        failed = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT ON (check_name) passed
                FROM ml.data_quality_results
                ORDER BY check_name, checked_at DESC, id DESC
            ) AS latest_checks
            WHERE NOT passed;
            """
        ).fetchone()
        freshness = connection.execute(
            "SELECT EXTRACT(EPOCH FROM now() - MAX(predicted_at)) FROM ml.flight_delay_predictions;"
        ).fetchone()
        delay_rate = connection.execute(
            """
            SELECT AVG(features.is_departure_delayed_15m::integer)::double precision
            FROM ml.flight_delay_predictions AS predictions
            JOIN ml.flight_delay_features AS features
                ON features.flight_id = predictions.flight_id
            WHERE features.is_departure_delayed_15m IS NOT NULL;
            """
        ).fetchone()
    if failed is None or freshness is None or delay_rate is None:
        raise RuntimeError("Monitoring queries returned no aggregate result.")
    DATA_QUALITY_FAILURES.set(int(failed[0]))
    PREDICTION_FRESHNESS.set(float(freshness[0]) if freshness[0] is not None else float("nan"))
    MATURED_LABEL_RATE.set(float(delay_rate[0]) if delay_rate[0] is not None else float("nan"))
    try:
        version = approved_model_version()
    except ApprovedModelUnavailable:
        LOGGER.warning(
            "Approved model version is unavailable during metrics collection.", exc_info=True
        )
        version = "unavailable"
    LOADED_MODEL.info({"name": MODEL_NAME, "version": version})
