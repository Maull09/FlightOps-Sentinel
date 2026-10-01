"""Binary-model evaluation and threshold policy."""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, roc_auc_score


def calculate_metrics(target: pd.Series, probabilities: NDArray[np.float64]) -> dict[str, float]:
    return {
        "roc_auc": float(roc_auc_score(target, probabilities)),
        "pr_auc": float(average_precision_score(target, probabilities)),
        "brier_score": float(brier_score_loss(target, probabilities)),
    }


def select_f1_threshold(target: pd.Series, probabilities: NDArray[np.float64]) -> float:
    candidates = np.arange(0.01, 1, 0.01)
    scores = [
        f1_score(target, probabilities >= candidate, zero_division=0) for candidate in candidates
    ]
    best_index = int(np.argmax(scores))
    return float(candidates[best_index])
