from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import flightops.training.tracking as tracking
from flightops.training.config import ExperimentConfig
from flightops.training.results import ExperimentResult


@pytest.fixture
def experiment_result() -> ExperimentResult:
    return ExperimentResult(
        model=MagicMock(),
        family="logistic",
        parameters={"max_iter": 1000},
        optuna_trials=[],
        snapshot={"row_count": 40},
        test_metrics={"roc_auc": 0.7, "pr_auc": 0.5, "brier_score": 0.1},
        plain_baseline_metrics={"roc_auc": 0.6, "pr_auc": 0.4},
        promotion_eligible=False,
        threshold=0.06,
        split_boundaries={
            "train": {"start": "2025-01-01T00:00:00+00:00", "end": "2025-01-24T00:00:00+00:00"}
        },
        row_counts={"total": 40, "train": 24, "validation": 8, "test": 8},
    )


@pytest.fixture
def tracking_dependencies(monkeypatch: pytest.MonkeyPatch):
    mlflow = MagicMock()
    mlflow.start_run.return_value.__enter__.return_value.info.run_id = "run-123"
    mlflow.register_model.return_value.version = "23"
    client = MagicMock()
    connection = MagicMock()
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow.test")
    monkeypatch.setattr(tracking, "mlflow", mlflow)
    monkeypatch.setattr(tracking, "MlflowClient", lambda: client)
    monkeypatch.setattr(tracking, "database_connection_string", lambda: "")
    monkeypatch.setattr(tracking.psycopg, "connect", lambda *args: connection)
    monkeypatch.setattr(
        tracking.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="abc123", returncode=0),
    )
    return mlflow, client, connection.__enter__.return_value


def test_tracking_records_real_split_lineage_and_comparator(
    experiment_config: ExperimentConfig, experiment_result: ExperimentResult, tracking_dependencies
) -> None:
    mlflow, client, connection = tracking_dependencies

    assert tracking.log_experiment(experiment_config, experiment_result) == "run-123"

    values = connection.execute.call_args.args[1]
    assert values[:4] == ("run-123", "flight-delay-risk", "23", False)
    assert json.loads(values[4]) == experiment_result.split_boundaries
    assert json.loads(values[5]) == experiment_result.row_counts
    assert json.loads(values[7]) == experiment_result.plain_baseline_metrics
    assert values[8] == "plain_logistic"
    mlflow.log_dict.assert_any_call({"trials": []}, "tuning/trials.json")
    client.set_registered_model_alias.assert_not_called()


def test_git_revision_marks_missing_git_as_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tracking.subprocess, "run", MagicMock(side_effect=FileNotFoundError("git")))

    assert tracking.git_revision() == "unavailable"


def test_git_revision_marks_a_non_repository_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tracking.subprocess,
        "run",
        MagicMock(return_value=SimpleNamespace(stdout="", returncode=128)),
    )

    assert tracking.git_revision() == "unavailable"


def test_eligible_model_is_promoted_after_lineage_is_recorded(
    experiment_config: ExperimentConfig, experiment_result: ExperimentResult, tracking_dependencies
) -> None:
    from dataclasses import replace

    _, client, connection = tracking_dependencies
    calls: list[str] = []
    connection.execute.side_effect = lambda *args: calls.append("lineage")
    client.set_registered_model_alias.side_effect = lambda *args: calls.append("promote")
    tracking.log_experiment(experiment_config, replace(experiment_result, promotion_eligible=True))

    assert calls == ["lineage", "promote"]
    client.set_registered_model_alias.assert_called_once_with("flight-delay-risk", "champion", "23")


def test_lineage_failure_prevents_promotion(
    experiment_config: ExperimentConfig, experiment_result: ExperimentResult, tracking_dependencies
) -> None:
    from dataclasses import replace

    _, client, connection = tracking_dependencies
    connection.execute.side_effect = RuntimeError("Database unavailable")

    with pytest.raises(RuntimeError, match="Database unavailable"):
        tracking.log_experiment(
            experiment_config, replace(experiment_result, promotion_eligible=True)
        )
    client.set_registered_model_alias.assert_not_called()
