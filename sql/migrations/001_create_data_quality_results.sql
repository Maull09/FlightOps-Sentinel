BEGIN;

CREATE TABLE ml.data_quality_results (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    checked_at timestamptz NOT NULL DEFAULT now(),
    check_name text NOT NULL,
    passed boolean NOT NULL,
    observed_value text NOT NULL,
    expected_value text NOT NULL
);

COMMIT;
