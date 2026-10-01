BEGIN;

ALTER TABLE ml.flight_delay_features
    ADD COLUMN booked_ticket_count integer NOT NULL DEFAULT 0,
    ADD COLUMN booked_revenue numeric(12, 2) NOT NULL DEFAULT 0,
    ADD COLUMN aircraft_seat_capacity integer NOT NULL DEFAULT 0,
    ADD COLUMN booked_load_factor double precision;

COMMIT;
