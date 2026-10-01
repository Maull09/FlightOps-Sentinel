"""Compare feature groups on the same chronological FlightOps holdout."""

from __future__ import annotations

import os
import sys

import mlflow
import mlflow.sklearn
from dotenv import load_dotenv
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from flightops.training.config import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    RAW_CALENDAR_COLUMNS,
    load_config,
)
from flightops.training.data import TARGET_COLUMN, TrainingData

SCHEDULE = RAW_CALENDAR_COLUMNS + ["scheduled_duration_minutes"]
STATIC = CATEGORICAL_FEATURES
HISTORY = [feature for feature in NUMERIC_FEATURES if feature.startswith("historical_")]
BOOKING = ["booked_ticket_count", "booked_revenue", "aircraft_seat_capacity", "booked_load_factor"]
GROUPS = {
    "schedule_only": (SCHEDULE, []),
    "schedule_static": (SCHEDULE, STATIC),
    "schedule_historical": (SCHEDULE + HISTORY, []),
    "schedule_booking": (SCHEDULE + BOOKING, []),
    "full_features": (NUMERIC_FEATURES + RAW_CALENDAR_COLUMNS, STATIC),
}


def build_model(numeric: list[str], categorical: list[str]) -> Pipeline:
    transformers = [
        (
            "numeric",
            Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]),
            numeric,
        )
    ]
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            )
        )
    return Pipeline(
        [
            ("preprocessor", ColumnTransformer(transformers)),
            ("classifier", LogisticRegression(max_iter=1_000, solver="liblinear", random_state=42)),
        ]
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(override=True)
    config = load_config("configs/training/logistic.yaml")
    data = TrainingData(config)
    train, validation, test = data.split(data.load())
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment("flight-delay-risk-ablation")
    results: dict[str, dict[str, float]] = {}
    with mlflow.start_run(run_name="ablation__feature-groups__chronological-v1"):
        for name, (numeric, categorical) in GROUPS.items():
            columns = numeric + categorical
            model = build_model(numeric, categorical)
            model.fit(train[columns], train[TARGET_COLUMN].astype(int))
            validation_probability = model.predict_proba(validation[columns])[:, 1]
            test_probability = model.predict_proba(test[columns])[:, 1]
            results[name] = {
                "validation_pr_auc": float(
                    average_precision_score(validation[TARGET_COLUMN], validation_probability)
                ),
                "test_roc_auc": float(roc_auc_score(test[TARGET_COLUMN], test_probability)),
                "test_pr_auc": float(
                    average_precision_score(test[TARGET_COLUMN], test_probability)
                ),
                "test_brier": float(brier_score_loss(test[TARGET_COLUMN], test_probability)),
            }
            mlflow.log_metrics({f"{name}_{key}": value for key, value in results[name].items()})
            mlflow.log_param(f"{name}_features", ",".join(columns))
        mlflow.log_dict(results, "evaluation/ablation_results.json")
    for name, metrics in results.items():
        print(name, metrics)


if __name__ == "__main__":
    main()
