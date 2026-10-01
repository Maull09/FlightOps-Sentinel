# Leakage Audit: T-24h Feature Mart

## Scope

Audit performed against `ml.flight_delay_features` after the Phase 3 materialization.

| Item | Result |
| --- | --- |
| Feature rows | 21,758 |
| Labelled rows | 10,986 |
| Fixed prediction horizon | T-24h |
| Forbidden columns in feature mart | 0 |
| Cutoff violations | 0 |
| Label parity mismatches | 0 |
| Sampled route-history mismatches | 0 |

## Historical-Feature Audit Method

The deterministic audit sample is every `flight_id` where `MOD(flight_id, 997) = 0` (21 rows in the current snapshot). For each sampled row, the stored route count and route delay rate are recalculated from source-derived staging data using only:

```text
history.actual_departure <= target.feature_cutoff
```

The sample recalculation found zero mismatches. This prevents a completed future flight from contributing its outcome to a target flight's features.

## Feature Exclusions

The feature mart does not contain `actual_departure`, `actual_arrival`, or `flight_status`. These remain only in staging/analytics for outcome labels and operational audit.

## Cold-History Behavior

4,241 feature rows have no completed route history at their T-24h cutoff. Their historical count is `0` and their historical rate is `null`. The SQL layer preserves that fact; handling it is an explicit training-pipeline decision in Phase 4.
