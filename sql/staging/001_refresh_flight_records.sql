BEGIN;

TRUNCATE TABLE staging.flight_records;

INSERT INTO staging.flight_records (
    flight_id,
    route_no,
    flight_status,
    scheduled_departure,
    scheduled_arrival,
    actual_departure,
    actual_arrival,
    departure_airport,
    arrival_airport,
    airplane_code,
    scheduled_duration,
    source_loaded_at
)
SELECT
    flights.flight_id,
    flights.route_no,
    flights.status,
    flights.scheduled_departure,
    flights.scheduled_arrival,
    flights.actual_departure,
    flights.actual_arrival,
    routes.departure_airport,
    routes.arrival_airport,
    routes.airplane_code,
    routes.duration,
    now()
FROM bookings.flights AS flights
JOIN bookings.routes AS routes
    ON routes.route_no = flights.route_no
    AND routes.validity @> flights.scheduled_departure;

COMMIT;
