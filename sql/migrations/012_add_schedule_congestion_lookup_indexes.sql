BEGIN;

CREATE INDEX flight_records_origin_scheduled_departure_idx
    ON staging.flight_records (departure_airport, scheduled_departure);

CREATE INDEX flight_records_destination_scheduled_arrival_idx
    ON staging.flight_records (arrival_airport, scheduled_arrival);

COMMIT;
