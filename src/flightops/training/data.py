"""Cutoff-safe training-data loading and chronological splitting."""

from __future__ import annotations

import pandas as pd
import psycopg

from flightops.database import database_connection_string
from flightops.training.config import ExperimentConfig

TARGET_COLUMN = "is_departure_delayed_15m"
TIME_COLUMN = "scheduled_departure"


class TrainingData:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    def load(self) -> pd.DataFrame:
        columns = ", ".join(self.config.input_features + [TIME_COLUMN, TARGET_COLUMN])
        query = (
            f"SELECT {columns} FROM ml.flight_delay_features "
            f"WHERE {TARGET_COLUMN} IS NOT NULL ORDER BY {TIME_COLUMN}, flight_id"
        )
        with psycopg.connect(database_connection_string()) as connection:
            data = pd.read_sql(query, connection)
        self.validate(data)
        return data

    def validate(self, data: pd.DataFrame) -> None:
        required_columns = self.config.input_features + [TIME_COLUMN, TARGET_COLUMN]
        missing_columns = sorted(set(required_columns) - set(data.columns))
        if missing_columns:
            raise ValueError(f"Missing training columns: {', '.join(missing_columns)}")
        self._validate_timestamps(data)
        if data[TARGET_COLUMN].isna().any() or not data[TARGET_COLUMN].isin([0, 1]).all():
            raise ValueError("Training targets must be labelled binary values.")

    def _validate_timestamps(self, data: pd.DataFrame) -> None:
        if data.empty:
            raise ValueError("Training data must be non-empty.")
        timestamps = data[TIME_COLUMN]
        if not isinstance(timestamps.dtype, pd.DatetimeTZDtype) or timestamps.isna().any():
            raise ValueError("Scheduled departures must be non-null, timezone-aware timestamps.")
        if not timestamps.is_monotonic_increasing:
            raise ValueError("Training data must be chronological.")

    def split(self, data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        self._validate_timestamps(data)
        times = data[TIME_COLUMN].drop_duplicates().reset_index(drop=True)
        train_count = int(len(times) * self.config.train_fraction)
        validation_end_index = int(
            len(times) * (self.config.train_fraction + self.config.validation_fraction)
        )
        if not 0 < train_count < validation_end_index < len(times):
            raise ValueError("Not enough unique timestamps for three non-empty split windows.")
        train_end = times.iloc[train_count - 1]
        validation_end = times.iloc[validation_end_index - 1]
        train = data.loc[data[TIME_COLUMN] <= train_end].copy()
        validation = data.loc[
            (data[TIME_COLUMN] > train_end) & (data[TIME_COLUMN] <= validation_end)
        ].copy()
        test = data.loc[data[TIME_COLUMN] > validation_end].copy()
        return train, validation, test

    def snapshot_metadata(self, data: pd.DataFrame) -> dict[str, object]:
        return {
            "row_count": len(data),
            "scheduled_departure_min": data[TIME_COLUMN].min().isoformat(),
            "scheduled_departure_max": data[TIME_COLUMN].max().isoformat(),
            "feature_columns": list(data.columns),
        }
