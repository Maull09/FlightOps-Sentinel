# Baseline Model and Evaluation

This document describes the initial Phase 4 evaluation. The current training workflow uses a plain logistic comparator and fixed serving bands; see [training pipeline](training-pipeline.md) and [MLflow lifecycle](mlflow-lifecycle.md). The historical route-rate experiment results remain in [baseline results](baseline-results.md).

## Model

The first candidate is unweighted logistic regression. It is intentionally interpretable and uses the T-24h feature contract only. The alert threshold, rather than class weighting, handles the operational trade-off between false alerts and missed delays; this preserves probability calibration for the Brier-score evaluation.

Numeric features use median imputation and standard scaling fitted on the training window. Categorical features use most-frequent imputation and one-hot encoding, also fitted on training only. Missing historical rates represent cold history; preprocessing is part of the learned pipeline, not a database fallback.

## Chronological Evaluation

Labelled flights are ordered by `scheduled_departure`. Unique timestamps are split into:

- first 60%: training;
- next 20%: validation;
- final 20%: future test.

No scheduled timestamp appears in more than one window. The validation window selects the initial alert threshold by maximum F1. The untouched test window reports ROC-AUC, PR-AUC, Brier score, precision, recall, F1, and confusion-matrix counts.

The non-ML comparator is the cutoff-safe historical route delay rate. Where no route history exists, it uses the training-window overall delayed-flight rate; this comparator is documented separately from the ML preprocessing.

For a future eligible candidate, the initial triage bands are `low` below half of the validation-selected alert threshold, `medium` from that half-threshold to the alert threshold, and `high` at or above the alert threshold. This is a provisional workflow convention only; it is not deployed while the candidate fails the comparator gate.

## Run Locally

```powershell
.\scripts\apply-migrations.ps1
.\.venv\Scripts\python.exe .\scripts\train-baseline.py
```

The command now runs the configured logistic workflow and prints an MLflow run ID. Current artifacts are stored by MLflow, including:

- the sklearn model under `model/`;
- dataset snapshot, split boundaries, and row counts under `lineage/`;
- selected parameters under `model/parameters.json` and Optuna trials under `tuning/trials.json`.
