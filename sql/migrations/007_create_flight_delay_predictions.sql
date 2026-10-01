BEGIN;

CREATE TABLE ml.flight_delay_predictions (
    flight_id integer NOT NULL REFERENCES ml.flight_delay_features (flight_id),
    feature_cutoff timestamptz NOT NULL,
    model_name text NOT NULL,
    model_version text NOT NULL,
    delay_risk_probability double precision NOT NULL,
    risk_level text NOT NULL CHECK (risk_level IN ('low', 'medium', 'high')),
    predicted_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (flight_id, feature_cutoff, model_name, model_version)
);

COMMIT;
