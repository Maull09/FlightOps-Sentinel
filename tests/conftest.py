from __future__ import annotations

import pandas as pd
import pytest

from flightops.training.config import ExperimentConfig, load_config
from flightops.training.data import TARGET_COLUMN, TIME_COLUMN


@pytest.fixture
def experiment_config() -> ExperimentConfig:
    return load_config("configs/training/logistic.yaml")


@pytest.fixture
def training_rows(experiment_config: ExperimentConfig) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index in range(40):
        row: dict[str, object] = {
            "scheduled_departure_hour": index % 24,
            "scheduled_departure_day_of_week": index % 7,
            "scheduled_departure_month": 1,
            "scheduled_duration_minutes": 90 + index,
            "route_no": "PG001",
            "departure_airport": "DME",
            "arrival_airport": "LED",
            "airplane_code": "319",
            TARGET_COLUMN: index % 2 == 0,
        }
        for feature in experiment_config.input_features:
            if feature.startswith("historical_"):
                row[feature] = 0.1 if feature.endswith("rate") else index
            elif feature not in row:
                row[feature] = index
        rows.append(row)
    data = pd.DataFrame(rows)
    data[TIME_COLUMN] = pd.date_range("2025-01-01", periods=len(data), freq="D", tz="UTC")
    return data
