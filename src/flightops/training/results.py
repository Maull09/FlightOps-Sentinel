"""The result passed from evaluation to experiment tracking."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.calibration import CalibratedClassifierCV


@dataclass(frozen=True)
class ExperimentResult:
    model: CalibratedClassifierCV
    family: str
    parameters: dict[str, object]
    optuna_trials: list[dict[str, object]]
    snapshot: dict[str, object]
    test_metrics: dict[str, float]
    plain_baseline_metrics: dict[str, float]
    promotion_eligible: bool
    threshold: float
    split_boundaries: dict[str, dict[str, str]]
    row_counts: dict[str, int]
