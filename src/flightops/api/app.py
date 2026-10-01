"""Internal HTTP API for approved flight-delay predictions."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import perf_counter

import pandas as pd
import psycopg
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from flightops.api.monitoring import (
    API_ERRORS,
    API_REQUEST_LATENCY,
    API_REQUESTS,
    PREDICTION_COUNT,
    PREDICTION_REQUESTS,
    refresh_monitoring_metrics,
)
from flightops.database import database_connection_string
from flightops.scoring.model import (
    MODEL_NAME,
    ApprovedModelUnavailable,
    approved_model_version,
    load_approved_model,
)
from flightops.scoring.policy import risk_level
from flightops.training.config import INPUT_FEATURES

LOGGER = logging.getLogger(__name__)
app = FastAPI(title="FlightOps Sentinel", version="0.1.0")


class PredictionResponse(BaseModel):
    flight_id: int
    prediction_timestamp: datetime
    delay_risk_probability: float
    risk_level: str
    model_name: str
    model_version: str


@app.middleware("http")
async def observe_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started = perf_counter()
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        path = getattr(request.scope.get("route"), "path", "unmatched")
        API_REQUESTS.labels(request.method, path, status_code).inc()
        API_REQUEST_LATENCY.labels(request.method, path).observe(perf_counter() - started)
        if status_code >= 400:
            API_ERRORS.labels(status_code).inc()


def load_eligible_features(flight_id: int, now: datetime) -> pd.DataFrame:
    """Load one feature row and enforce the T-24h operating window."""

    query = f"""
        SELECT flight_id, feature_cutoff, scheduled_departure, {", ".join(INPUT_FEATURES)}
        FROM ml.flight_delay_features
        WHERE flight_id = %s;
    """
    with psycopg.connect(database_connection_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (flight_id,))
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found."
                )
            if cursor.description is None:
                raise RuntimeError("Feature query returned no column metadata.")
            columns = [item.name for item in cursor.description]

    features = pd.DataFrame([row], columns=columns)
    cutoff = features.at[0, "feature_cutoff"]
    departure = features.at[0, "scheduled_departure"]
    if cutoff > now or departure <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flight is not eligible for a T-24h prediction.",
        )
    return features


@app.get("/health")
def health() -> dict[str, str]:
    """Report process health without claiming an approved model is available."""

    return {"status": "ok"}


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    try:
        approved_model_version()
    except ApprovedModelUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No approved model version is available.",
        ) from error
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    refresh_monitoring_metrics()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/predictions/flight-delay", response_model=PredictionResponse)
def predict_flight_delay(flight_id: int) -> PredictionResponse:
    """Return a delay-risk prediction for one eligible flight."""

    PREDICTION_REQUESTS.inc()
    now = datetime.now(UTC)
    features = load_eligible_features(flight_id, now)
    try:
        model, model_version = load_approved_model()
    except ApprovedModelUnavailable as error:
        LOGGER.warning("Approved model is unavailable for prediction.", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No approved model is available for prediction.",
        ) from error

    probability = float(model.predict_proba(features[INPUT_FEATURES])[:, 1][0])
    PREDICTION_COUNT.labels(model_version).inc()
    return PredictionResponse(
        flight_id=flight_id,
        prediction_timestamp=now,
        delay_risk_probability=probability,
        risk_level=risk_level(probability),
        model_name=MODEL_NAME,
        model_version=model_version,
    )
