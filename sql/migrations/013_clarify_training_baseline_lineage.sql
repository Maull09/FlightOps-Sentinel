BEGIN;

ALTER TABLE ml.training_runs
    RENAME COLUMN candidate_beats_route_rate_baseline TO candidate_beats_baseline;
ALTER TABLE ml.training_runs
    RENAME COLUMN route_rate_baseline_test_metrics TO baseline_test_metrics;
ALTER TABLE ml.training_runs
    ADD COLUMN baseline_name text;

-- Existing runs used different comparators; do not infer their identity from old column names.
COMMENT ON COLUMN ml.training_runs.baseline_name IS
    'Comparator used by this run. NULL means the legacy run did not record its identity.';

COMMIT;
