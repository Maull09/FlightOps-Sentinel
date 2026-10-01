BEGIN;

ALTER TABLE ml.flight_delay_features
    ADD COLUMN historical_destination_completed_count integer NOT NULL DEFAULT 0,
    ADD COLUMN historical_destination_delay_rate double precision,
    ADD COLUMN historical_route_hour_completed_count integer NOT NULL DEFAULT 0,
    ADD COLUMN historical_route_hour_delay_rate double precision,
    ADD CONSTRAINT flight_delay_features_destination_count_nonnegative
        CHECK (historical_destination_completed_count >= 0),
    ADD CONSTRAINT flight_delay_features_route_hour_count_nonnegative
        CHECK (historical_route_hour_completed_count >= 0);

COMMIT;
