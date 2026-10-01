"""Versioned YAML configuration for reproducible experiments."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

NUMERIC_FEATURES = [
    "scheduled_duration_minutes",
    "historical_route_completed_count",
    "historical_route_delay_rate",
    "historical_origin_completed_count",
    "historical_origin_delay_rate",
    "historical_aircraft_completed_count",
    "historical_aircraft_delay_rate",
    "historical_destination_completed_count",
    "historical_destination_delay_rate",
    "historical_route_hour_completed_count",
    "historical_route_hour_delay_rate",
    "historical_route_30d_completed_count",
    "historical_route_30d_delay_rate",
    "historical_origin_30d_completed_count",
    "historical_origin_30d_delay_rate",
    "historical_destination_30d_completed_count",
    "historical_destination_30d_delay_rate",
    "historical_route_weekday_hour_completed_count",
    "historical_route_weekday_hour_delay_rate",
    "booked_ticket_count",
    "booked_revenue",
    "aircraft_seat_capacity",
    "booked_load_factor",
    "booked_ticket_count_last_7d",
    "booked_ticket_count_last_30d",
    "booked_ticket_average_lead_time_hours",
    "origin_scheduled_departures_2h",
    "destination_scheduled_arrivals_2h",
]
CATEGORICAL_FEATURES = ["route_no", "departure_airport", "arrival_airport", "airplane_code"]
RAW_CALENDAR_COLUMNS = [
    "scheduled_departure_hour",
    "scheduled_departure_day_of_week",
    "scheduled_departure_month",
]
PLAIN_NUMERIC_FEATURES = ["scheduled_duration_minutes"]
PLAIN_FEATURES = RAW_CALENDAR_COLUMNS + PLAIN_NUMERIC_FEATURES
INPUT_FEATURES = RAW_CALENDAR_COLUMNS + NUMERIC_FEATURES + CATEGORICAL_FEATURES


@dataclass(frozen=True)
class ExperimentConfig:
    path: Path
    name: str
    version: str
    seed: int
    family: str
    parameters: dict[str, object]
    tuning_enabled: bool
    trials: int
    feature_version: str
    train_fraction: float
    validation_fraction: float

    def __post_init__(self) -> None:
        if not 0 < self.train_fraction < 1 or not 0 < self.validation_fraction < 1:
            raise ValueError("Training and validation fractions must be between 0 and 1.")
        if self.train_fraction + self.validation_fraction >= 1:
            raise ValueError("Split fractions must leave a non-empty future test window.")
        if self.tuning_enabled and self.trials <= 0:
            raise ValueError("Enabled tuning requires a positive trial count.")

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    @property
    def input_features(self) -> list[str]:
        return INPUT_FEATURES.copy()


def load_config(path: str | Path) -> ExperimentConfig:
    source = Path(path)
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    return ExperimentConfig(
        path=source,
        name=raw["experiment"]["name"],
        version=raw["experiment"]["version"],
        seed=raw["experiment"]["seed"],
        family=raw["model"]["family"],
        parameters=raw["model"].get("parameters", {}),
        tuning_enabled=raw["tuning"]["enabled"],
        trials=raw["tuning"]["trials"],
        feature_version=raw["data"]["feature_version"],
        train_fraction=raw["data"]["train_fraction"],
        validation_fraction=raw["data"]["validation_fraction"],
    )
