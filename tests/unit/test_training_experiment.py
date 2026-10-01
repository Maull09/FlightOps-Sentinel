from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, roc_auc_score

from flightops.training.config import ExperimentConfig
from flightops.training.data import TARGET_COLUMN, TrainingData
from flightops.training.experiment import TrainingExperiment
from flightops.training.models import build_plain_baseline, get_model_factory


def test_refactored_training_preserves_predictions_and_evaluation(
    experiment_config: ExperimentConfig,
    training_rows: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiment = TrainingExperiment(experiment_config)
    monkeypatch.setattr(experiment.data, "load", lambda: training_rows)
    result = experiment.run()

    train, validation, test = TrainingData(experiment_config).split(training_rows)
    features = experiment_config.input_features
    pipeline = get_model_factory("logistic").build_pipeline(
        experiment_config, experiment_config.parameters
    )
    pipeline.fit(train[features], train[TARGET_COLUMN].astype(int))
    reference_model = CalibratedClassifierCV(pipeline, method="sigmoid", cv="prefit")
    reference_model.fit(validation[features], validation[TARGET_COLUMN].astype(int))
    probabilities = reference_model.predict_proba(test[features])[:, 1]
    baseline = build_plain_baseline(experiment_config)
    baseline.fit(train[features], train[TARGET_COLUMN].astype(int))
    baseline_probabilities = baseline.predict_proba(test[features])[:, 1]

    np.testing.assert_allclose(result.model.predict_proba(test[features])[:, 1], probabilities)
    assert result.test_metrics == {
        "roc_auc": roc_auc_score(test[TARGET_COLUMN], probabilities),
        "pr_auc": average_precision_score(test[TARGET_COLUMN], probabilities),
        "brier_score": brier_score_loss(test[TARGET_COLUMN], probabilities),
    }
    assert result.plain_baseline_metrics == {
        "roc_auc": roc_auc_score(test[TARGET_COLUMN], baseline_probabilities),
        "pr_auc": average_precision_score(test[TARGET_COLUMN], baseline_probabilities),
    }
    assert result.promotion_eligible == all(
        result.test_metrics[name] > result.plain_baseline_metrics[name]
        for name in ("roc_auc", "pr_auc")
    )
    validation_probabilities = reference_model.predict_proba(validation[features])[:, 1]
    thresholds = np.arange(0.01, 1, 0.01)
    scores = [
        f1_score(validation[TARGET_COLUMN], validation_probabilities >= value, zero_division=0)
        for value in thresholds
    ]
    assert result.threshold == thresholds[np.argmax(scores)]
    assert result.row_counts == {"total": 40, "train": 24, "validation": 8, "test": 8}
    assert result.split_boundaries["train"]["end"] < result.split_boundaries["validation"]["start"]
    assert result.split_boundaries["validation"]["end"] < result.split_boundaries["test"]["start"]


@pytest.mark.parametrize("window", ["train", "validation", "test"])
def test_training_rejects_a_single_class_window(
    experiment_config: ExperimentConfig,
    training_rows: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    window: str,
) -> None:
    windows = dict(
        zip(
            ("train", "validation", "test"),
            TrainingData(experiment_config).split(training_rows),
            strict=True,
        )
    )
    training_rows.loc[windows[window].index, TARGET_COLUMN] = False
    experiment = TrainingExperiment(experiment_config)
    monkeypatch.setattr(experiment.data, "load", lambda: training_rows)

    with pytest.raises(ValueError, match=f"{window} window must contain both target classes"):
        experiment.run()


def test_tuning_does_not_use_the_future_test_window(
    experiment_config: ExperimentConfig,
    training_rows: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = replace(experiment_config, tuning_enabled=True, trials=2)
    train, validation, test = TrainingData(config).split(training_rows)
    factory = get_model_factory("logistic")
    build_pipeline = factory.build_pipeline
    fitted_indices: list[list[int]] = []
    predicted_indices: list[list[int]] = []

    def recording_pipeline(*args):
        model = build_pipeline(*args)
        fit = model.fit
        predict_proba = model.predict_proba

        def recording_fit(data, target):
            fitted_indices.append(list(data.index))
            return fit(data, target)

        def recording_predict(data):
            predicted_indices.append(list(data.index))
            return predict_proba(data)

        model.fit = recording_fit
        model.predict_proba = recording_predict
        return model

    monkeypatch.setattr(factory, "build_pipeline", recording_pipeline)
    parameters, trials = TrainingExperiment(config)._tune_parameters(factory, train, validation)

    assert parameters == config.parameters
    assert len(trials) == 2
    assert fitted_indices == [list(train.index)] * 2
    assert predicted_indices == [list(validation.index)] * 2
    assert set(test.index).isdisjoint(index for indices in predicted_indices for index in indices)
