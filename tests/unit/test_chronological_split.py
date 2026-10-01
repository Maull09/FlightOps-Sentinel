from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from flightops.training.config import ExperimentConfig, load_config
from flightops.training.data import TIME_COLUMN, TrainingData


def test_chronological_split_keeps_timestamps_in_one_window() -> None:
    data = pd.DataFrame(
        {
            TIME_COLUMN: pd.to_datetime(
                [
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T00:00:00Z",
                    "2025-01-02T00:00:00Z",
                    "2025-01-03T00:00:00Z",
                    "2025-01-04T00:00:00Z",
                    "2025-01-05T00:00:00Z",
                ]
            ),
            "is_departure_delayed_15m": [False, True, False, True, False, True],
        }
    )

    config = load_config("configs/training/logistic.yaml")
    train, validation, test = TrainingData(config).split(data)

    assert train[TIME_COLUMN].max() < validation[TIME_COLUMN].min()
    assert validation[TIME_COLUMN].max() < test[TIME_COLUMN].min()


def test_split_uses_configured_fractions(
    experiment_config: ExperimentConfig, training_rows: pd.DataFrame
) -> None:
    config = replace(experiment_config, train_fraction=0.5, validation_fraction=0.25)
    windows = TrainingData(config).split(training_rows)

    assert [len(window) for window in windows] == [20, 10, 10]


def test_split_rejects_insufficient_unique_timestamps(
    experiment_config: ExperimentConfig, training_rows: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match="Not enough unique timestamps"):
        TrainingData(experiment_config).split(training_rows.head(2))


@pytest.mark.parametrize(
    ("train_fraction", "validation_fraction"), [(0, 0.2), (0.6, -0.1), (0.8, 0.2)]
)
def test_config_rejects_invalid_split_fractions(
    experiment_config: ExperimentConfig, train_fraction: float, validation_fraction: float
) -> None:
    with pytest.raises(ValueError, match="fraction"):
        replace(
            experiment_config,
            train_fraction=train_fraction,
            validation_fraction=validation_fraction,
        )
