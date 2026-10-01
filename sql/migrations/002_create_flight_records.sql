BEGIN;

CREATE TABLE staging.flight_records (
    flight_id integer PRIMARY KEY,
    route_no text NOT NULL,
    flight_status text NOT NULL,
    scheduled_departure timestamptz NOT NULL,
    scheduled_arrival timestamptz NOT NULL,
    actual_departure timestamptz,
    actual_arrival timestamptz,
    departure_airport char(3) NOT NULL,
    arrival_airport char(3) NOT NULL,
    airplane_code char(3) NOT NULL,
    scheduled_duration interval NOT NULL,
    source_loaded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT flight_records_scheduled_time_order
        CHECK (scheduled_arrival > scheduled_departure),
    CONSTRAINT flight_records_actual_time_order
        CHECK (
            actual_arrival IS NULL
            OR (actual_departure IS NOT NULL AND actual_arrival > actual_departure)
        )
);

CREATE INDEX flight_records_scheduled_departure_idx
    ON staging.flight_records (scheduled_departure);

CREATE INDEX flight_records_route_no_idx
    ON staging.flight_records (route_no);

COMMIT;
