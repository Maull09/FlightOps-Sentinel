# MLflow Lifecycle

## Experiment and Registry

The tracking server is configured by `MLFLOW_TRACKING_URI`; the experiment name comes from the selected YAML file. Every candidate workflow run logs:

- model and feature parameters;
- chronological split boundaries and row counts;
- test ROC-AUC, PR-AUC, candidate Brier score, and plain-logistic comparator metrics;
- dataset, feature, split, parameter, and trial JSON artifacts;
- a scikit-learn model artifact;
- candidate/promotion tags.
- the configured family, Optuna trials with validation PR-AUC, and validation F1 threshold.

The registered model name is `flight-delay-risk`. Each registered version receives an `eligible` or `rejected` `promotion_status` tag. The current logger does not provide an explicit model signature, input example, or calibration plot.

## Promotion Rule

A candidate is eligible only when it improves on the future test window against the plain logistic comparator using raw calendar and scheduled duration:

1. ROC-AUC is higher;
2. PR-AUC is higher;

Brier score is logged for the candidate as a calibration diagnostic, but it is neither logged for the baseline nor used as a promotion criterion.

Tracking automatically sets `champion` for an eligible version after PostgreSQL lineage is saved. A rejected candidate remains registered and leaves the existing champion unchanged. Separate family runs are separate experiments; the tracker does not choose a finalist across families. See the [training pipeline](training-pipeline.md) for holdout and validation limitations.

## PostgreSQL Lineage

`ml.training_runs` maps MLflow run IDs to registered model versions, actual split boundaries, per-window row counts, test metrics, comparator identity, and the promotion decision. Migration `013_clarify_training_baseline_lineage.sql` renames the misleading route-rate fields to `candidate_beats_baseline` and `baseline_test_metrics`, and adds `baseline_name`. New runs record `plain_logistic`; legacy rows retain `NULL` because their comparator cannot safely be inferred from their old column names. Historical numeric metrics are preserved.

## Run

```powershell
.\scripts\apply-migrations.ps1
.\.venv\Scripts\python.exe .\scripts\train-candidates.py
```

The script evaluates, logs, registers, records lineage, and conditionally promotes the model. It prints the run ID. It does not reload the registered artifact or perform a live fixture prediction; use the local platform smoke test to verify deployed inference.
