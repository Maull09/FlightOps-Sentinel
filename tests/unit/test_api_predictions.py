from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from flightops.api.app import app, load_eligible_features
from flightops.api.monitoring import API_REQUESTS
from flightops.scoring.model import ApprovedModelUnavailable


@pytest.fixture
def feature_cursor(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    connection = MagicMock()
    cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
    monkeypatch.setattr("flightops.api.app.database_connection_string", lambda: "")
    monkeypatch.setattr("flightops.api.app.psycopg.connect", lambda *args: connection)
    return cursor


def test_unknown_flight_returns_not_found(feature_cursor: MagicMock) -> None:
    feature_cursor.fetchone.return_value = None
    with pytest.raises(HTTPException) as failure:
        load_eligible_features(123, datetime.now(UTC))
    assert failure.value.status_code == 404


@pytest.mark.parametrize(
    ("cutoff_offset", "departure_offset", "eligible"),
    [(0, 24, True), (-1, 23, True), (1, 25, False), (-24, 0, False), (-25, -1, False)],
)
def test_t24h_eligibility_boundaries(
    feature_cursor: MagicMock, cutoff_offset: int, departure_offset: int, eligible: bool
) -> None:
    now = datetime(2025, 1, 1, tzinfo=UTC)
    feature_cursor.description = [
        SimpleNamespace(name=name)
        for name in ["flight_id", "feature_cutoff", "scheduled_departure"]
    ]
    feature_cursor.fetchone.return_value = (
        123,
        now + timedelta(hours=cutoff_offset),
        now + timedelta(hours=departure_offset),
    )
    if eligible:
        assert load_eligible_features(123, now).at[0, "flight_id"] == 123
    else:
        with pytest.raises(HTTPException) as failure:
            load_eligible_features(123, now)
        assert failure.value.status_code == 400


def test_prediction_reports_the_loaded_model_version(
    training_rows: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = MagicMock()
    model.predict_proba.return_value = np.array([[0.96, 0.04]])
    monkeypatch.setattr(
        "flightops.api.app.load_eligible_features", lambda *args: training_rows.head(1)
    )
    monkeypatch.setattr("flightops.api.app.load_approved_model", lambda: (model, "23"))

    response = TestClient(app).post("/v1/predictions/flight-delay?flight_id=123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "23"
    assert payload["risk_level"] == "medium"
    assert payload["delay_risk_probability"] == 0.04
    assert datetime.fromisoformat(payload["prediction_timestamp"]).utcoffset() == timedelta(0)


def test_prediction_returns_service_unavailable_for_missing_champion(
    training_rows: pd.DataFrame, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "flightops.api.app.load_eligible_features", lambda *args: training_rows.head(1)
    )
    monkeypatch.setattr(
        "flightops.api.app.load_approved_model", MagicMock(side_effect=ApprovedModelUnavailable())
    )
    response = TestClient(app).post("/v1/predictions/flight-delay?flight_id=123")
    assert response.status_code == 503
    assert response.json()["detail"] == "No approved model is available for prediction."
    assert "Approved model is unavailable for prediction" in caplog.text


def test_readiness_reports_registry_unavailability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "flightops.api.app.approved_model_version",
        MagicMock(side_effect=ApprovedModelUnavailable()),
    )
    assert TestClient(app).get("/health/ready").status_code == 503


def test_unknown_paths_share_one_metric_label() -> None:
    counter = API_REQUESTS.labels("GET", "unmatched", "404")
    before = counter._value.get()
    client = TestClient(app)
    client.get("/missing-one")
    client.get("/missing-two")
    assert counter._value.get() - before == 2


def test_unhandled_errors_are_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "flightops.api.app.refresh_monitoring_metrics",
        MagicMock(side_effect=RuntimeError("Database offline")),
    )
    counter = API_REQUESTS.labels("GET", "/metrics", "500")
    before = counter._value.get()
    response = TestClient(app, raise_server_exceptions=False).get("/metrics")
    assert response.status_code == 500
    assert counter._value.get() - before == 1
