import pickle
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from mlflow.exceptions import MlflowException

from flightops.scoring.model import ApprovedModelUnavailable, load_approved_model


def test_alias_is_resolved_once_and_the_exact_version_is_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client.get_model_version_by_alias.side_effect = [
        SimpleNamespace(version="23"),
        SimpleNamespace(version="24"),
    ]
    loader = MagicMock(return_value=object())
    monkeypatch.setattr("flightops.scoring.model.MlflowClient", lambda: client)
    monkeypatch.setattr("flightops.scoring.model.mlflow.sklearn.load_model", loader)

    model, version = load_approved_model()

    assert model is loader.return_value
    assert version == "23"
    client.get_model_version_by_alias.assert_called_once_with("flight-delay-risk", "champion")
    loader.assert_called_once_with("models:/flight-delay-risk/23")


def test_missing_champion_does_not_load_a_model(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.get_model_version_by_alias.side_effect = MlflowException("Alias does not exist")
    loader = MagicMock()
    monkeypatch.setattr("flightops.scoring.model.MlflowClient", lambda: client)
    monkeypatch.setattr("flightops.scoring.model.mlflow.sklearn.load_model", loader)

    with pytest.raises(ApprovedModelUnavailable, match="No approved model"):
        load_approved_model()
    loader.assert_not_called()


def test_artifact_failure_keeps_the_original_error_context(monkeypatch: pytest.MonkeyPatch) -> None:
    error = EOFError("Truncated artifact")
    monkeypatch.setattr("flightops.scoring.model.approved_model_version", lambda: "23")
    monkeypatch.setattr(
        "flightops.scoring.model.mlflow.sklearn.load_model", MagicMock(side_effect=error)
    )
    with pytest.raises(ApprovedModelUnavailable, match="version 23") as failure:
        load_approved_model()
    assert failure.value.__cause__ is error


@pytest.mark.parametrize(
    "error", [EOFError("Truncated artifact"), pickle.UnpicklingError("Invalid artifact")]
)
def test_deserialization_failures_are_reported_as_an_unavailable_model(
    error: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("flightops.scoring.model.approved_model_version", lambda: "23")
    monkeypatch.setattr(
        "flightops.scoring.model.mlflow.sklearn.load_model", MagicMock(side_effect=error)
    )

    with pytest.raises(ApprovedModelUnavailable, match="version 23") as failure:
        load_approved_model()

    assert failure.value.__cause__ is error
