"""Train, calibrate, and evaluate one configured model family."""

from __future__ import annotations

import optuna
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import average_precision_score

from flightops.training.config import ExperimentConfig
from flightops.training.data import TARGET_COLUMN, TIME_COLUMN, TrainingData
from flightops.training.evaluation import calculate_metrics, select_f1_threshold
from flightops.training.models import ModelFactory, build_plain_baseline, get_model_factory
from flightops.training.results import ExperimentResult
from flightops.training.tracking import log_experiment


class TrainingExperiment:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.data = TrainingData(config)

    def run(self) -> ExperimentResult:
        data = self.data.load()
        train, validation, test = self.data.split(data)
        windows = {"train": train, "validation": validation, "test": test}
        for name, window in windows.items():
            if window[TARGET_COLUMN].nunique() != 2:
                raise ValueError(f"The {name} window must contain both target classes.")

        factory = get_model_factory(self.config.family)
        parameters, trials = self._tune_parameters(factory, train, validation)
        model = self._fit_calibrated_model(factory, parameters, train, validation)
        test_metrics, baseline_metrics = self._evaluate_models(model, train, test)
        validation_probabilities = model.predict_proba(validation[self.config.input_features])[:, 1]
        return ExperimentResult(
            model=model,
            family=self.config.family,
            parameters=parameters,
            optuna_trials=trials,
            snapshot=self.data.snapshot_metadata(data),
            test_metrics=test_metrics,
            plain_baseline_metrics=baseline_metrics,
            promotion_eligible=(
                test_metrics["roc_auc"] > baseline_metrics["roc_auc"]
                and test_metrics["pr_auc"] > baseline_metrics["pr_auc"]
            ),
            threshold=select_f1_threshold(validation[TARGET_COLUMN], validation_probabilities),
            split_boundaries={
                name: {
                    "start": window[TIME_COLUMN].min().isoformat(),
                    "end": window[TIME_COLUMN].max().isoformat(),
                }
                for name, window in windows.items()
            },
            row_counts={"total": len(data)}
            | {name: len(window) for name, window in windows.items()},
        )

    def _tune_parameters(
        self, factory: ModelFactory, train: pd.DataFrame, validation: pd.DataFrame
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        parameters = dict(self.config.parameters)
        trials: list[dict[str, object]] = []
        if not self.config.tuning_enabled:
            return parameters, trials

        def objective(trial: optuna.Trial) -> float:
            trial_parameters = parameters | factory.search_space(trial)
            model = factory.build_pipeline(self.config, trial_parameters)
            model.fit(train[self.config.input_features], train[TARGET_COLUMN].astype(int))
            probabilities = model.predict_proba(validation[self.config.input_features])[:, 1]
            score = float(average_precision_score(validation[TARGET_COLUMN], probabilities))
            trials.append({"number": trial.number, "parameters": trial_parameters, "pr_auc": score})
            return score

        study = optuna.create_study(
            direction="maximize", sampler=optuna.samplers.TPESampler(seed=self.config.seed)
        )
        study.optimize(objective, n_trials=self.config.trials)
        parameters.update(study.best_params)
        return parameters, trials

    def _fit_calibrated_model(
        self,
        factory: ModelFactory,
        parameters: dict[str, object],
        train: pd.DataFrame,
        validation: pd.DataFrame,
    ) -> CalibratedClassifierCV:
        model = factory.build_pipeline(self.config, parameters)
        model.fit(train[self.config.input_features], train[TARGET_COLUMN].astype(int))
        calibrated = CalibratedClassifierCV(model, method="sigmoid", cv="prefit")
        calibrated.fit(
            validation[self.config.input_features], validation[TARGET_COLUMN].astype(int)
        )
        return calibrated

    def _evaluate_models(
        self, model: CalibratedClassifierCV, train: pd.DataFrame, test: pd.DataFrame
    ) -> tuple[dict[str, float], dict[str, float]]:
        probabilities = model.predict_proba(test[self.config.input_features])[:, 1]
        test_metrics = calculate_metrics(test[TARGET_COLUMN], probabilities)
        baseline = build_plain_baseline(self.config)
        baseline.fit(train[self.config.input_features], train[TARGET_COLUMN].astype(int))
        baseline_probabilities = baseline.predict_proba(test[self.config.input_features])[:, 1]
        baseline_metrics = calculate_metrics(test[TARGET_COLUMN], baseline_probabilities)
        comparison_metrics = {
            "roc_auc": baseline_metrics["roc_auc"],
            "pr_auc": baseline_metrics["pr_auc"],
        }
        return test_metrics, comparison_metrics

    def track(self, result: ExperimentResult) -> str:
        return log_experiment(self.config, result)
