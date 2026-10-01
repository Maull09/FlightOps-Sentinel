BEGIN;

CREATE VIEW analytics.flight_delay_labels AS
SELECT
    flight_id,
    scheduled_departure,
    actual_departure,
    CASE
        WHEN actual_departure IS NULL THEN NULL
        WHEN actual_departure > scheduled_departure + INTERVAL '15 minutes' THEN true
        ELSE false
    END AS is_departure_delayed_15m
FROM staging.flight_records;

COMMIT;
