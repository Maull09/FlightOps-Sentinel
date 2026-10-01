"""MLflow lineage for complete sklearn pipelines."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime

import mlflow
import mlflow.sklearn
import psycopg
from mlflow import MlflowClient

from flightops.database import database_connection_string
from flightops.scoring.model import APPROVED_MODEL_ALIAS, MODEL_NAME
from flightops.training.config import ExperimentConfig
from flightops.training.results import ExperimentResult


def log_experiment(config: ExperimentConfig, result: ExperimentResult) -> str:
    """Track and register a candidate, persist lineage, then promote eligible versions."""

    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment(config.name)
    run_id = _log_run(config, result)
    model_version = _register_model(run_id, result)
    _record_training_run(run_id, model_version, result)
    if result.promotion_eligible:
        MlflowClient().set_registered_model_alias(MODEL_NAME, APPROVED_MODEL_ALIAS, model_version)
    return run_id


def _log_run(config: ExperimentConfig, result: ExperimentResult) -> str:
    revision = git_revision()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_name = f"{config.version}__{config.family}__{config.hash[:8]}__{timestamp}"
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(
            {
                "config_file": config.path.name,
                "config_hash": config.hash,
                "git_revision": revision,
                "feature_version": config.feature_version,
                "model_family": config.family,
                "experiment_version": config.version,
                "run_name": run_name,
                "pipeline_steps": "calendar,history,drop_raw_calendar,preprocessor,classifier",
            }
        )
        mlflow.log_dict(
            {
                "input_features": config.input_features,
                "feature_engineering": (
                    "cutoff-safe SQL history plus sklearn calendar/history transformers"
                ),
            },
            "lineage/features.json",
        )
        mlflow.log_artifact(str(config.path), "config")
        mlflow.log_dict(result.snapshot, "lineage/dataset_snapshot.json")
        mlflow.log_dict(result.split_boundaries, "lineage/split_boundaries.json")
        mlflow.log_dict(result.row_counts, "lineage/row_counts.json")
        mlflow.log_dict(result.parameters, "model/parameters.json")
        mlflow.log_dict({"trials": result.optuna_trials}, "tuning/trials.json")
        mlflow.log_param("risk_threshold", result.threshold)
        mlflow.log_param("baseline_name", "plain_logistic")
        mlflow.log_metrics(result.test_metrics)
        mlflow.log_metrics(
            {f"plain_baseline_{key}": value for key, value in result.plain_baseline_metrics.items()}
        )
        mlflow.set_tag("promotion_eligible", str(result.promotion_eligible).lower())
        mlflow.sklearn.log_model(result.model, "model")
        run_id = str(run.info.run_id)
    return run_id


def git_revision() -> str:
    """Return the repository revision when Git metadata is available to the runtime."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        )
    except OSError:
        return "unavailable"
    revision = result.stdout.strip()
    return revision if result.returncode == 0 and revision else "unavailable"


def _register_model(run_id: str, result: ExperimentResult) -> str:
    registered = mlflow.register_model(f"runs:/{run_id}/model", MODEL_NAME)
    client = MlflowClient()
    client.set_model_version_tag(
        MODEL_NAME,
        registered.version,
        "promotion_status",
        "eligible" if result.promotion_eligible else "rejected",
    )
    return str(registered.version)


def _record_training_run(run_id: str, model_version: str, result: ExperimentResult) -> None:
    with psycopg.connect(database_connection_string()) as connection:
        connection.execute(
            """
            INSERT INTO ml.training_runs (
                mlflow_run_id, model_name, registered_model_version,
                candidate_beats_baseline, split_boundaries, row_counts,
                test_metrics, baseline_test_metrics, baseline_name
            ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)
            ON CONFLICT (mlflow_run_id) DO NOTHING;
            """,
            (
                run_id,
                MODEL_NAME,
                model_version,
                result.promotion_eligible,
                json.dumps(result.split_boundaries),
                json.dumps(result.row_counts),
                json.dumps(result.test_metrics),
                json.dumps(result.plain_baseline_metrics),
                "plain_logistic",
            ),
        )
        connection.commit()
