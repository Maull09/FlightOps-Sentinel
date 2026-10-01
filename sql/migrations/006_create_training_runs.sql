BEGIN;

CREATE TABLE ml.training_runs (
    mlflow_run_id text PRIMARY KEY,
    model_name text NOT NULL,
    registered_model_version text,
    candidate_beats_route_rate_baseline boolean NOT NULL,
    split_boundaries jsonb NOT NULL,
    row_counts jsonb NOT NULL,
    test_metrics jsonb NOT NULL,
    route_rate_baseline_test_metrics jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
