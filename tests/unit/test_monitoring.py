from math import isnan
from unittest.mock import MagicMock

import pytest

from flightops.api.monitoring import (
    DATA_QUALITY_FAILURES,
    LOADED_MODEL,
    MATURED_LABEL_RATE,
    PREDICTION_FRESHNESS,
    refresh_monitoring_metrics,
)
from flightops.scoring.model import ApprovedModelUnavailable


def test_empty_monitoring_history_is_unknown_and_missing_champion_is_visible(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    connection = MagicMock()
    connection.__enter__.return_value.execute.return_value.fetchone.side_effect = [
        (0,),
        (None,),
        (None,),
    ]
    monkeypatch.setattr("flightops.api.monitoring.database_connection_string", lambda: "")
    monkeypatch.setattr("flightops.api.monitoring.psycopg.connect", lambda *args: connection)
    monkeypatch.setattr(
        "flightops.api.monitoring.approved_model_version",
        MagicMock(side_effect=ApprovedModelUnavailable()),
    )

    refresh_monitoring_metrics()

    assert DATA_QUALITY_FAILURES._value.get() == 0
    assert isnan(PREDICTION_FRESHNESS._value.get())
    assert isnan(MATURED_LABEL_RATE._value.get())
    assert LOADED_MODEL._value["version"] == "unavailable"
    assert "unavailable during metrics collection" in caplog.text
