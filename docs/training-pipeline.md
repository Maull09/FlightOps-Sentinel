# Training Pipeline

Each invocation trains the model family selected by one YAML configuration. The training workflow uses small modules with explicit responsibilities:

1. `training.config` reads model parameters and split fractions from YAML. `INPUT_FEATURES` is the shared raw input contract used by training, API, and batch scoring.
2. `training.data` reads labelled rows from PostgreSQL, validates required columns, non-empty chronological data, timezone-aware timestamps, and binary labels, then splits unique scheduled timestamps using the configured fractions. Missing historical rates are allowed for cold history; imputation is fitted within the sklearn pipeline.
3. `training.models` builds an estimator and its shared preprocessing pipeline. Calendar/history transformers and the raw-calendar dropper live in `training.features`.
4. `TrainingExperiment` tunes enabled families with a seeded Optuna study: every trial fits the training window and scores PR-AUC on validation. It then fits the selected parameters on training and calibrates the candidate with sigmoid calibration on validation. Each train/validation/test window must contain both classes.
5. `training.evaluation` calculates future-test ROC-AUC, PR-AUC, and candidate Brier score. Validation F1 selects a diagnostic threshold. The plain logistic comparator uses raw calendar values and scheduled duration, with no history or categorical features. A candidate is eligible only if both ROC-AUC and PR-AUC exceed this comparator.
6. `ExperimentResult` carries the fitted model, parameters, trials, metrics, real split boundaries, and per-window row counts. `training.tracking` logs these, registers the version, and records PostgreSQL lineage. Eligible versions receive the `champion` alias after lineage is saved; rejected versions are registered without replacing it.

## Experiment Families

Available configs are `logistic.yaml`, `xgboost.yaml`, `lightgbm.yaml`, `random-forest.yaml`, and `extra-trees-balanced.yaml`. Logistic tuning is disabled by default; the other files specify their Optuna trial counts.

Run from the repository root with PostgreSQL and MLflow running, `.env` configured, and migrations applied:

```powershell
.\scripts\apply-migrations.ps1
.\.venv\Scripts\python.exe scripts\validate-training-data.py configs\training\logistic.yaml
.\.venv\Scripts\python.exe scripts\train-candidates.py configs\training\logistic.yaml
.\.venv\Scripts\python.exe scripts\train-candidates.py configs\training\xgboost.yaml
```

`train-baseline.py` runs the same workflow with the logistic config. The Airflow training task also runs evaluation and tracking. Both CLI training scripts print the MLflow run ID. The batch scorer and API resolve `champion` once and load `models:/flight-delay-risk/<resolved-version>` so each prediction records the version actually loaded.

## Evaluation Limitations

The current workflow shares validation between tuning, calibration, and threshold selection. It does not perform an inner chronological cross-validation loop or automatically select across all five families. Repeatedly comparing separate family runs on the same test window can bias selection; reserve a new holdout when changing the selection policy.

The current gate compares against plain logistic regression. Earlier route-rate results in `baseline-results.md` are historical evidence for a previous workflow. The fixed operational risk bands remain 0.03 and 0.06; the validation-selected F1 threshold is logged for analysis and does not change serving bands.

`cv="prefit"` is supported by the pinned sklearn 1.6 range but emits a deprecation warning. Before upgrading sklearn, migrate calibration to `FrozenEstimator` and verify predictions against the current workflow.
