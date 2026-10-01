BEGIN;

CREATE TABLE ml.flight_delay_features (
    flight_id integer PRIMARY KEY,
    feature_cutoff timestamptz NOT NULL,
    scheduled_departure timestamptz NOT NULL,
    is_departure_delayed_15m boolean,
    scheduled_departure_hour smallint NOT NULL,
    scheduled_departure_day_of_week smallint NOT NULL,
    scheduled_departure_month smallint NOT NULL,
    route_no text NOT NULL,
    departure_airport char(3) NOT NULL,
    arrival_airport char(3) NOT NULL,
    airplane_code char(3) NOT NULL,
    scheduled_duration_minutes integer NOT NULL,
    historical_route_completed_count integer NOT NULL,
    historical_route_delay_rate double precision,
    historical_origin_completed_count integer NOT NULL,
    historical_origin_delay_rate double precision,
    historical_aircraft_completed_count integer NOT NULL,
    historical_aircraft_delay_rate double precision,
    materialized_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT flight_delay_features_cutoff
        CHECK (feature_cutoff = scheduled_departure - INTERVAL '24 hours'),
    CONSTRAINT flight_delay_features_hour_range
        CHECK (scheduled_departure_hour BETWEEN 0 AND 23),
    CONSTRAINT flight_delay_features_day_of_week_range
        CHECK (scheduled_departure_day_of_week BETWEEN 0 AND 6),
    CONSTRAINT flight_delay_features_month_range
        CHECK (scheduled_departure_month BETWEEN 1 AND 12),
    CONSTRAINT flight_delay_features_duration_positive
        CHECK (scheduled_duration_minutes > 0),
    CONSTRAINT flight_delay_features_route_count_nonnegative
        CHECK (historical_route_completed_count >= 0),
    CONSTRAINT flight_delay_features_origin_count_nonnegative
        CHECK (historical_origin_completed_count >= 0),
    CONSTRAINT flight_delay_features_aircraft_count_nonnegative
        CHECK (historical_aircraft_completed_count >= 0)
);

CREATE INDEX flight_delay_features_scheduled_departure_idx
    ON ml.flight_delay_features (scheduled_departure);

COMMIT;
