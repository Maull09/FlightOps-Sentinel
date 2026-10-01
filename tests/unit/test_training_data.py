from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock

import pandas as pd
import pytest

from flightops.training.config import ExperimentConfig
from flightops.training.data import TARGET_COLUMN, TIME_COLUMN, TrainingData


def test_validation_accepts_missing_history_rates(
    experiment_config: ExperimentConfig, training_rows: pd.DataFrame
) -> None:
    training_rows.loc[0, "historical_route_delay_rate"] = float("nan")
    TrainingData(experiment_config).validate(training_rows)


@pytest.mark.parametrize("invalid_target", [None, 2, "delayed"])
def test_validation_rejects_invalid_targets(
    experiment_config: ExperimentConfig, training_rows: pd.DataFrame, invalid_target: object
) -> None:
    training_rows[TARGET_COLUMN] = training_rows[TARGET_COLUMN].astype(object)
    training_rows.loc[0, TARGET_COLUMN] = invalid_target
    with pytest.raises(ValueError, match="labelled binary"):
        TrainingData(experiment_config).validate(training_rows)


def test_validation_rejects_missing_features(
    experiment_config: ExperimentConfig, training_rows: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match="Missing training columns: route_no"):
        TrainingData(experiment_config).validate(training_rows.drop(columns="route_no"))


def test_validation_rejects_empty_data(
    experiment_config: ExperimentConfig, training_rows: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        TrainingData(experiment_config).validate(training_rows.head(0))


def test_validation_rejects_naive_timestamps(
    experiment_config: ExperimentConfig, training_rows: pd.DataFrame
) -> None:
    training_rows[TIME_COLUMN] = training_rows[TIME_COLUMN].dt.tz_localize(None)
    with pytest.raises(ValueError, match="timezone-aware"):
        TrainingData(experiment_config).validate(training_rows)


def test_validation_rejects_unordered_data(
    experiment_config: ExperimentConfig, training_rows: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match="chronological"):
        TrainingData(experiment_config).validate(training_rows.iloc[::-1])


def test_loading_validates_the_returned_dataset(
    experiment_config: ExperimentConfig,
    training_rows: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("flightops.training.data.database_connection_string", lambda: "")
    monkeypatch.setattr("flightops.training.data.psycopg.connect", MagicMock())
    monkeypatch.setattr(
        "flightops.training.data.pd.read_sql",
        lambda *args: training_rows.drop(columns=TARGET_COLUMN),
    )
    with pytest.raises(ValueError, match=TARGET_COLUMN):
        TrainingData(experiment_config).load()


def test_enabled_tuning_requires_trials(experiment_config: ExperimentConfig) -> None:
    with pytest.raises(ValueError, match="positive trial count"):
        replace(experiment_config, tuning_enabled=True, trials=0)
