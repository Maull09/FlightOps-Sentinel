from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from flightops.scoring.batch import score_flights


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime(2025, 1, 1), datetime(2025, 1, 2, tzinfo=UTC)),
        (datetime(2025, 1, 2, tzinfo=UTC), datetime(2025, 1, 1, tzinfo=UTC)),
        (datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 1, 1, tzinfo=UTC)),
    ],
)
def test_invalid_intervals_fail_before_loading_a_model(
    start: datetime, end: datetime, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader = MagicMock()
    monkeypatch.setattr("flightops.scoring.batch.load_approved_model", loader)
    with pytest.raises(ValueError):
        score_flights(start, end)
    loader.assert_not_called()


def test_batch_records_the_loaded_version_and_shared_risk_bands(
    training_rows: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows = training_rows.head(3).copy()
    rows["flight_id"] = [1, 2, 3]
    rows["feature_cutoff"] = start
    model = MagicMock()
    model.predict_proba.return_value = np.array([[0.98, 0.02], [0.96, 0.04], [0.9, 0.1]])
    connection = MagicMock()
    cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.rowcount = 3
    monkeypatch.setattr("flightops.scoring.batch.database_connection_string", lambda: "")
    monkeypatch.setattr("flightops.scoring.batch.psycopg.connect", lambda *args: connection)
    monkeypatch.setattr("flightops.scoring.batch.pd.read_sql", lambda *args, **kwargs: rows)
    monkeypatch.setattr("flightops.scoring.batch.load_approved_model", lambda: (model, "23"))

    assert score_flights(start, start + timedelta(days=1)) == 3
    stored_rows = cursor.executemany.call_args.args[1]
    assert [row[3] for row in stored_rows] == ["23", "23", "23"]
    assert [row[5] for row in stored_rows] == ["low", "medium", "high"]
