BEGIN;

-- Local development refresh policy: predictions depend on this feature snapshot.
-- Clear the project-owned prediction cache before rebuilding the feature mart.
TRUNCATE TABLE ml.flight_delay_predictions, ml.flight_delay_features;

WITH base_flights AS (
    SELECT
        records.flight_id,
        records.scheduled_departure - INTERVAL '24 hours' AS feature_cutoff,
        records.scheduled_departure,
        records.scheduled_arrival,
        labels.is_departure_delayed_15m,
        EXTRACT(HOUR FROM records.scheduled_departure AT TIME ZONE airports.timezone)::smallint
            AS scheduled_departure_hour,
        EXTRACT(DOW FROM records.scheduled_departure AT TIME ZONE airports.timezone)::smallint
            AS scheduled_departure_day_of_week,
        EXTRACT(MONTH FROM records.scheduled_departure AT TIME ZONE airports.timezone)::smallint
            AS scheduled_departure_month,
        records.route_no,
        records.departure_airport,
        records.arrival_airport,
        records.airplane_code,
        EXTRACT(EPOCH FROM records.scheduled_duration)::integer / 60
            AS scheduled_duration_minutes
    FROM staging.flight_records AS records
    JOIN analytics.flight_delay_labels AS labels
        ON labels.flight_id = records.flight_id
    JOIN bookings.airports_data AS airports
        ON airports.airport_code = records.departure_airport
)
INSERT INTO ml.flight_delay_features (
    flight_id,
    feature_cutoff,
    scheduled_departure,
    is_departure_delayed_15m,
    scheduled_departure_hour,
    scheduled_departure_day_of_week,
    scheduled_departure_month,
    route_no,
    departure_airport,
    arrival_airport,
    airplane_code,
    scheduled_duration_minutes,
    historical_route_completed_count,
    historical_route_delay_rate,
    historical_origin_completed_count,
    historical_origin_delay_rate,
    historical_aircraft_completed_count,
    historical_aircraft_delay_rate,
    historical_destination_completed_count,
    historical_destination_delay_rate,
    historical_route_hour_completed_count,
    historical_route_hour_delay_rate,
    historical_route_30d_completed_count,
    historical_route_30d_delay_rate,
    historical_origin_30d_completed_count,
    historical_origin_30d_delay_rate,
    historical_destination_30d_completed_count,
    historical_destination_30d_delay_rate,
    historical_route_weekday_hour_completed_count,
    historical_route_weekday_hour_delay_rate,
    booked_ticket_count,
    booked_revenue,
    aircraft_seat_capacity,
    booked_load_factor,
    booked_ticket_count_last_7d,
    booked_ticket_count_last_30d,
    booked_ticket_average_lead_time_hours,
    origin_scheduled_departures_2h,
    destination_scheduled_arrivals_2h,
    materialized_at
)
SELECT
    base.flight_id,
    base.feature_cutoff,
    base.scheduled_departure,
    base.is_departure_delayed_15m,
    base.scheduled_departure_hour,
    base.scheduled_departure_day_of_week,
    base.scheduled_departure_month,
    base.route_no,
    base.departure_airport,
    base.arrival_airport,
    base.airplane_code,
    base.scheduled_duration_minutes,
    route_history.completed_count,
    route_history.delay_rate,
    origin_history.completed_count,
    origin_history.delay_rate,
    aircraft_history.completed_count,
    aircraft_history.delay_rate,
    destination_history.completed_count,
    destination_history.delay_rate,
    route_hour_history.completed_count,
    route_hour_history.delay_rate,
    route_30d_history.completed_count,
    route_30d_history.delay_rate,
    origin_30d_history.completed_count,
    origin_30d_history.delay_rate,
    destination_30d_history.completed_count,
    destination_30d_history.delay_rate,
    route_weekday_hour_history.completed_count,
    route_weekday_hour_history.delay_rate,
    booking_demand.ticket_count,
    booking_demand.revenue,
    seat_capacity.seat_count,
    CASE
        WHEN seat_capacity.seat_count = 0 THEN NULL
        ELSE booking_demand.ticket_count::double precision / seat_capacity.seat_count
    END,
    booking_demand.ticket_count_last_7d,
    booking_demand.ticket_count_last_30d,
    booking_demand.average_lead_time_hours,
    origin_schedule.departure_count,
    destination_schedule.arrival_count,
    now()
FROM base_flights AS base
LEFT JOIN LATERAL (
    SELECT
        COUNT(*)::integer AS completed_count,
        AVG((history.actual_departure > history.scheduled_departure + INTERVAL '15 minutes')::integer)::double precision
            AS delay_rate
    FROM staging.flight_records AS history
    WHERE history.route_no = base.route_no
        AND history.actual_departure <= base.feature_cutoff
) AS route_history ON true
LEFT JOIN LATERAL (
    SELECT
        COUNT(*)::integer AS completed_count,
        AVG((history.actual_departure > history.scheduled_departure + INTERVAL '15 minutes')::integer)::double precision
            AS delay_rate
    FROM staging.flight_records AS history
    WHERE history.departure_airport = base.departure_airport
        AND history.actual_departure <= base.feature_cutoff
) AS origin_history ON true
LEFT JOIN LATERAL (
    SELECT
        COUNT(*)::integer AS completed_count,
        AVG((history.actual_departure > history.scheduled_departure + INTERVAL '15 minutes')::integer)::double precision
            AS delay_rate
    FROM staging.flight_records AS history
    WHERE history.airplane_code = base.airplane_code
        AND history.actual_departure <= base.feature_cutoff
) AS aircraft_history ON true
LEFT JOIN LATERAL (
    SELECT COUNT(*)::integer AS completed_count,
        AVG((history.actual_departure > history.scheduled_departure + INTERVAL '15 minutes')::integer)::double precision AS delay_rate
    FROM staging.flight_records AS history
    WHERE history.arrival_airport = base.arrival_airport
      AND history.actual_departure <= base.feature_cutoff
) AS destination_history ON true
LEFT JOIN LATERAL (
    SELECT COUNT(*)::integer AS completed_count,
        AVG((history.actual_departure > history.scheduled_departure + INTERVAL '15 minutes')::integer)::double precision AS delay_rate
    FROM staging.flight_records AS history
    JOIN bookings.airports_data AS history_airport ON history_airport.airport_code = history.departure_airport
    WHERE history.route_no = base.route_no
      AND EXTRACT(HOUR FROM history.scheduled_departure AT TIME ZONE history_airport.timezone)::smallint = base.scheduled_departure_hour
      AND history.actual_departure <= base.feature_cutoff
) AS route_hour_history ON true
LEFT JOIN LATERAL (
    SELECT COUNT(*)::integer AS completed_count,
        AVG((history.actual_departure > history.scheduled_departure + INTERVAL '15 minutes')::integer)::double precision AS delay_rate
    FROM staging.flight_records AS history
    WHERE history.route_no = base.route_no
      AND history.actual_departure <= base.feature_cutoff
      AND history.actual_departure > base.feature_cutoff - INTERVAL '30 days'
) AS route_30d_history ON true
LEFT JOIN LATERAL (
    SELECT COUNT(*)::integer AS completed_count,
        AVG((history.actual_departure > history.scheduled_departure + INTERVAL '15 minutes')::integer)::double precision AS delay_rate
    FROM staging.flight_records AS history
    WHERE history.departure_airport = base.departure_airport
      AND history.actual_departure <= base.feature_cutoff
      AND history.actual_departure > base.feature_cutoff - INTERVAL '30 days'
) AS origin_30d_history ON true
LEFT JOIN LATERAL (
    SELECT COUNT(*)::integer AS completed_count,
        AVG((history.actual_departure > history.scheduled_departure + INTERVAL '15 minutes')::integer)::double precision AS delay_rate
    FROM staging.flight_records AS history
    WHERE history.arrival_airport = base.arrival_airport
      AND history.actual_departure <= base.feature_cutoff
      AND history.actual_departure > base.feature_cutoff - INTERVAL '30 days'
) AS destination_30d_history ON true
LEFT JOIN LATERAL (
    SELECT COUNT(*)::integer AS completed_count,
        AVG((history.actual_departure > history.scheduled_departure + INTERVAL '15 minutes')::integer)::double precision AS delay_rate
    FROM staging.flight_records AS history
    JOIN bookings.airports_data AS history_airport ON history_airport.airport_code = history.departure_airport
    WHERE history.route_no = base.route_no
      AND EXTRACT(DOW FROM history.scheduled_departure AT TIME ZONE history_airport.timezone)::smallint = base.scheduled_departure_day_of_week
      AND EXTRACT(HOUR FROM history.scheduled_departure AT TIME ZONE history_airport.timezone)::smallint = base.scheduled_departure_hour
      AND history.actual_departure <= base.feature_cutoff
) AS route_weekday_hour_history ON true
LEFT JOIN LATERAL (
    SELECT
        COUNT(DISTINCT segments.ticket_no)::integer AS ticket_count,
        COALESCE(SUM(segments.price), 0)::numeric(12, 2) AS revenue,
        COUNT(DISTINCT segments.ticket_no) FILTER (
            WHERE reservations.book_date > base.feature_cutoff - INTERVAL '7 days'
        )::integer AS ticket_count_last_7d,
        COUNT(DISTINCT segments.ticket_no) FILTER (
            WHERE reservations.book_date > base.feature_cutoff - INTERVAL '30 days'
        )::integer AS ticket_count_last_30d,
        AVG(
            EXTRACT(EPOCH FROM (base.scheduled_departure - reservations.book_date)) / 3600.0
        )::double precision AS average_lead_time_hours
    FROM bookings.segments AS segments
    JOIN bookings.tickets AS tickets ON tickets.ticket_no = segments.ticket_no
    JOIN bookings.bookings AS reservations ON reservations.book_ref = tickets.book_ref
    WHERE segments.flight_id = base.flight_id
      AND reservations.book_date <= base.feature_cutoff
) AS booking_demand ON true
LEFT JOIN LATERAL (
    SELECT COUNT(*)::integer AS departure_count
    FROM staging.flight_records AS scheduled
    WHERE scheduled.departure_airport = base.departure_airport
        AND scheduled.flight_id <> base.flight_id
        AND scheduled.scheduled_departure >= base.scheduled_departure - INTERVAL '1 hour'
        AND scheduled.scheduled_departure < base.scheduled_departure + INTERVAL '1 hour'
) AS origin_schedule ON true
LEFT JOIN LATERAL (
    SELECT COUNT(*)::integer AS arrival_count
    FROM staging.flight_records AS scheduled
    WHERE scheduled.arrival_airport = base.arrival_airport
        AND scheduled.flight_id <> base.flight_id
        AND scheduled.scheduled_arrival >= base.scheduled_arrival - INTERVAL '1 hour'
        AND scheduled.scheduled_arrival < base.scheduled_arrival + INTERVAL '1 hour'
) AS destination_schedule ON true
LEFT JOIN LATERAL (
    SELECT COUNT(*)::integer AS seat_count
    FROM bookings.seats AS seats
    WHERE seats.airplane_code = base.airplane_code
) AS seat_capacity ON true;

COMMIT;
