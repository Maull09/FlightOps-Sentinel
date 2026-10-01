"""Resolve the approved alias once and load that exact model version."""

from __future__ import annotations

import pickle
from typing import Any

import mlflow.sklearn
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

MODEL_NAME = "flight-delay-risk"
APPROVED_MODEL_ALIAS = "champion"


class ApprovedModelUnavailable(RuntimeError):
    """The approved registry version or its model artifact is unavailable."""


def approved_model_version() -> str:
    try:
        version = MlflowClient().get_model_version_by_alias(MODEL_NAME, APPROVED_MODEL_ALIAS)
    except MlflowException as error:
        raise ApprovedModelUnavailable("No approved model version is available.") from error
    return str(version.version)


def load_approved_model() -> tuple[Any, str]:
    version = approved_model_version()
    try:
        model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{version}")
    except (EOFError, ImportError, OSError, pickle.UnpicklingError) as error:
        raise ApprovedModelUnavailable(f"Cannot load approved model version {version}.") from error
    return model, version
