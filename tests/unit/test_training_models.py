from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from flightops.training.config import load_config
from flightops.training.data import TARGET_COLUMN
from flightops.training.models import get_model_factory


@pytest.mark.parametrize(
    "config_path",
    [
        "configs/training/logistic.yaml",
        "configs/training/xgboost.yaml",
        "configs/training/lightgbm.yaml",
        "configs/training/random-forest.yaml",
        "configs/training/extra-trees-balanced.yaml",
    ],
)
def test_registered_model_families_build_probability_pipelines(
    config_path: str, training_rows: pd.DataFrame
) -> None:
    config = load_config(config_path)
    model = get_model_factory(config.family).build_pipeline(config, config.parameters)
    model.fit(training_rows[config.input_features], training_rows[TARGET_COLUMN])
    assert model.predict_proba(training_rows[config.input_features]).shape == (
        len(training_rows),
        2,
    )


def test_unknown_family_fails_explicitly() -> None:
    with pytest.raises(ValueError, match="Unsupported model family"):
        get_model_factory("catboost")


def test_serialized_pipeline_preserves_predictions(
    training_rows: pd.DataFrame, tmp_path: Path
) -> None:
    config = load_config("configs/training/logistic.yaml")
    model = get_model_factory(config.family).build_pipeline(config, config.parameters)
    inputs = training_rows[config.input_features]
    model.fit(inputs, training_rows[TARGET_COLUMN])
    artifact = tmp_path / "model.joblib"

    joblib.dump(model, artifact)
    loaded = joblib.load(artifact)

    np.testing.assert_allclose(loaded.predict_proba(inputs), model.predict_proba(inputs))
