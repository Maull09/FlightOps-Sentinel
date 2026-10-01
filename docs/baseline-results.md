# Baseline Evaluation Results

## Evaluation Window

The labelled feature mart was split chronologically by scheduled departure:

| Window | Rows | End boundary |
| --- | ---: | --- |
| Training | 6,575 | 2025-11-06 15:30:00+00 |
| Validation | 2,205 | 2025-11-18 18:50:00+00 |
| Test | 2,206 | Future holdout after validation boundary |

The delayed-flight rates were 4.76% (training), 6.08% (validation), and 4.99% (test).

## Test Metrics

| Candidate | ROC-AUC | PR-AUC | Brier score |
| --- | ---: | ---: | ---: |
| Logistic regression | 0.4836 | 0.0503 | 0.0514 |
| Historical route delay rate | 0.5437 | 0.0642 | 0.0494 |

The logistic-regression candidate does not improve ranking, precision-recall performance, or calibration over the non-ML route-rate comparator.

## Alert Threshold

The validation window selected a high-risk alert threshold of `0.06` by maximum F1. The provisional medium threshold is `0.03`; lower scores are low risk. On the future test window the high-risk threshold produced:

| Metric | Value |
| --- | ---: |
| Precision | 4.87% |
| Recall | 53.64% |
| F1 | 8.93% |
| True positives | 59 |
| False positives | 1,152 |
| False negatives | 51 |

## Decision

**Do not promote the logistic-regression candidate.** It loses to the simpler historical route-rate baseline on all three comparison metrics. Phase 5 may log this run to MLflow for traceability, but no model should be promoted to a production alias or registry stage.

## Limitations and Next Experiments

- The airline demo snapshot has limited completed history and only a small number of delayed outcomes.
- The current source lacks external operational predictors such as weather, aircraft rotation, staffing, and live airport congestion.
- Future experiments should be evaluated only after adding features with a demonstrably cutoff-safe availability contract.
- A stronger model alone is not justified until a candidate first exceeds the simple baseline on the future holdout window.
