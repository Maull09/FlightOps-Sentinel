"""Registered model factories and shared sklearn preprocessing."""

from __future__ import annotations

from typing import Any, cast

from lightgbm import LGBMClassifier
from optuna import Trial
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from flightops.training.config import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    PLAIN_FEATURES,
    ExperimentConfig,
)
from flightops.training.features import (
    CalendarFeatureTransformer,
    FeatureDropper,
    HistoryFeatureTransformer,
)

ENGINEERED_NUMERIC_FEATURES = (
    NUMERIC_FEATURES
    + [
        f"{column}_{suffix}"
        for column in [
            "scheduled_departure_hour",
            "scheduled_departure_day_of_week",
            "scheduled_departure_month",
        ]
        for suffix in ["sin", "cos"]
    ]
    + [
        f"{column}_missing"
        for column in [
            "historical_route_delay_rate",
            "historical_origin_delay_rate",
            "historical_aircraft_delay_rate",
            "historical_destination_delay_rate",
            "historical_route_hour_delay_rate",
        ]
    ]
    + [
        f"{column}_cold_start"
        for column in [
            "historical_route_completed_count",
            "historical_origin_completed_count",
            "historical_aircraft_completed_count",
            "historical_destination_completed_count",
            "historical_route_hour_completed_count",
        ]
    ]
)


class ModelFactory:
    family = ""

    def build_estimator(self, config: ExperimentConfig, parameters: dict[str, object]) -> Any:
        raise NotImplementedError

    def search_space(self, trial: Trial) -> dict[str, object]:
        return {}

    def numeric_preprocessing_steps(self) -> list[tuple[str, Any]]:
        return [("imputer", SimpleImputer(strategy="median"))]

    def build_pipeline(self, config: ExperimentConfig, parameters: dict[str, object]) -> Pipeline:
        preprocessor = ColumnTransformer(
            [
                (
                    "numeric",
                    Pipeline(self.numeric_preprocessing_steps()),
                    ENGINEERED_NUMERIC_FEATURES,
                ),
                (
                    "categorical",
                    Pipeline(
                        [
                            ("imputer", SimpleImputer(strategy="most_frequent")),
                            ("encoder", OneHotEncoder(handle_unknown="ignore")),
                        ]
                    ),
                    CATEGORICAL_FEATURES,
                ),
            ]
        )
        return Pipeline(
            [
                ("calendar", CalendarFeatureTransformer()),
                ("history", HistoryFeatureTransformer()),
                ("drop_raw_calendar", FeatureDropper()),
                ("preprocessor", preprocessor),
                ("classifier", self.build_estimator(config, parameters)),
            ]
        )


class LogisticFactory(ModelFactory):
    family = "logistic"

    def numeric_preprocessing_steps(self) -> list[tuple[str, Any]]:
        return super().numeric_preprocessing_steps() + [("scaler", StandardScaler())]

    def build_estimator(
        self, config: ExperimentConfig, parameters: dict[str, object]
    ) -> LogisticRegression:
        return LogisticRegression(random_state=config.seed, **parameters)


class XGBoostFactory(ModelFactory):
    family = "xgboost"

    def build_estimator(
        self, config: ExperimentConfig, parameters: dict[str, object]
    ) -> XGBClassifier:
        return XGBClassifier(random_state=config.seed, n_jobs=1, **parameters)

    def search_space(self, trial: Trial) -> dict[str, object]:
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 400),
            "max_depth": trial.suggest_int("max_depth", 2, 6),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        }


class LightGBMFactory(ModelFactory):
    family = "lightgbm"

    def build_estimator(
        self, config: ExperimentConfig, parameters: dict[str, object]
    ) -> LGBMClassifier:
        return LGBMClassifier(
            random_state=config.seed, n_jobs=1, **cast(dict[str, Any], parameters)
        )

    def search_space(self, trial: Trial) -> dict[str, object]:
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 400),
            "num_leaves": trial.suggest_int("num_leaves", 7, 31),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        }


class RandomForestFactory(ModelFactory):
    family = "random_forest"

    def build_estimator(
        self, config: ExperimentConfig, parameters: dict[str, object]
    ) -> RandomForestClassifier:
        return RandomForestClassifier(random_state=config.seed, n_jobs=1, **parameters)

    def search_space(self, trial: Trial) -> dict[str, object]:
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        }


class ExtraTreesFactory(ModelFactory):
    family = "extra_trees"

    def build_estimator(
        self, config: ExperimentConfig, parameters: dict[str, object]
    ) -> ExtraTreesClassifier:
        return ExtraTreesClassifier(random_state=config.seed, n_jobs=1, **parameters)

    def search_space(self, trial: Trial) -> dict[str, object]:
        return {
            "n_estimators": trial.suggest_int("n_estimators", 200, 600),
            "max_depth": trial.suggest_int("max_depth", 3, 24),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 12),
            "max_features": trial.suggest_float("max_features", 0.4, 1.0),
        }


MODEL_FACTORIES = {
    factory.family: factory
    for factory in [
        LogisticFactory(),
        XGBoostFactory(),
        LightGBMFactory(),
        RandomForestFactory(),
        ExtraTreesFactory(),
    ]
}


def get_model_factory(family: str) -> ModelFactory:
    try:
        return MODEL_FACTORIES[family]
    except KeyError as error:
        supported = ", ".join(sorted(MODEL_FACTORIES))
        raise ValueError(f"Unsupported model family '{family}'. Supported: {supported}.") from error


def build_plain_baseline(config: ExperimentConfig) -> Pipeline:
    """Build the no-feature-engineering logistic comparator."""

    preprocessor = ColumnTransformer(
        [("numeric", SimpleImputer(strategy="median"), PLAIN_FEATURES)]
    )
    return Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "classifier",
                LogisticRegression(max_iter=1_000, solver="liblinear", random_state=config.seed),
            ),
        ]
    )
