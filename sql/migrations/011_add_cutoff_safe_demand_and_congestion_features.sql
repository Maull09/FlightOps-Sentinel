BEGIN;

ALTER TABLE ml.flight_delay_features
    ADD COLUMN booked_ticket_count_last_7d integer NOT NULL DEFAULT 0,
    ADD COLUMN booked_ticket_count_last_30d integer NOT NULL DEFAULT 0,
    ADD COLUMN booked_ticket_average_lead_time_hours double precision,
    ADD COLUMN origin_scheduled_departures_2h integer NOT NULL DEFAULT 0,
    ADD COLUMN destination_scheduled_arrivals_2h integer NOT NULL DEFAULT 0,
    ADD CONSTRAINT flight_delay_features_booking_7d_nonnegative
        CHECK (booked_ticket_count_last_7d >= 0),
    ADD CONSTRAINT flight_delay_features_booking_30d_nonnegative
        CHECK (booked_ticket_count_last_30d >= 0),
    ADD CONSTRAINT flight_delay_features_booking_lead_time_cutoff_safe
        CHECK (
            booked_ticket_average_lead_time_hours IS NULL
            OR booked_ticket_average_lead_time_hours >= 24
        ),
    ADD CONSTRAINT flight_delay_features_origin_congestion_nonnegative
        CHECK (origin_scheduled_departures_2h >= 0),
    ADD CONSTRAINT flight_delay_features_destination_congestion_nonnegative
        CHECK (destination_scheduled_arrivals_2h >= 0);

COMMIT;
