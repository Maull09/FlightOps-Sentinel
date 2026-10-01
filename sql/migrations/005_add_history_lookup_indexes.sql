BEGIN;

CREATE INDEX flight_records_route_actual_departure_idx
    ON staging.flight_records (route_no, actual_departure)
    WHERE actual_departure IS NOT NULL;

CREATE INDEX flight_records_origin_actual_departure_idx
    ON staging.flight_records (departure_airport, actual_departure)
    WHERE actual_departure IS NOT NULL;

CREATE INDEX flight_records_aircraft_actual_departure_idx
    ON staging.flight_records (airplane_code, actual_departure)
    WHERE actual_departure IS NOT NULL;

COMMIT;
