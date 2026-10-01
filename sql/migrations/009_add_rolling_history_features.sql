BEGIN;

ALTER TABLE ml.flight_delay_features
    ADD COLUMN historical_route_30d_completed_count integer NOT NULL DEFAULT 0,
    ADD COLUMN historical_route_30d_delay_rate double precision,
    ADD COLUMN historical_origin_30d_completed_count integer NOT NULL DEFAULT 0,
    ADD COLUMN historical_origin_30d_delay_rate double precision,
    ADD COLUMN historical_destination_30d_completed_count integer NOT NULL DEFAULT 0,
    ADD COLUMN historical_destination_30d_delay_rate double precision,
    ADD COLUMN historical_route_weekday_hour_completed_count integer NOT NULL DEFAULT 0,
    ADD COLUMN historical_route_weekday_hour_delay_rate double precision;

COMMIT;
