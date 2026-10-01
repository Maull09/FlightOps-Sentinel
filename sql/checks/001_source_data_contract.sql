WITH source_checks AS (
    SELECT
        'source_flights_table_exists' AS check_name,
        to_regclass('bookings.flights') IS NOT NULL AS passed,
        COALESCE(to_regclass('bookings.flights')::text, 'missing') AS observed_value,
        'bookings.flights exists' AS expected_value

    UNION ALL

    SELECT
        'source_flights_required_columns_exist',
        COUNT(*) = 7,
        COUNT(*)::text,
        '7 required columns'
    FROM information_schema.columns
    WHERE table_schema = 'bookings'
        AND table_name = 'flights'
        AND column_name IN (
            'flight_id',
            'route_no',
            'status',
            'scheduled_departure',
            'scheduled_arrival',
            'actual_departure',
            'actual_arrival'
        )

    UNION ALL

    SELECT
        'source_flights_has_rows',
        COUNT(*) > 0,
        COUNT(*)::text,
        '> 0 rows'
    FROM bookings.flights

    UNION ALL

    SELECT
        'source_flight_id_is_unique',
        COUNT(*) = COUNT(DISTINCT flight_id),
        (COUNT(*) - COUNT(DISTINCT flight_id))::text,
        '0 duplicate flight_id values'
    FROM bookings.flights

    UNION ALL

    SELECT
        'source_scheduled_times_are_ordered',
        COUNT(*) FILTER (WHERE scheduled_arrival <= scheduled_departure) = 0,
        COUNT(*) FILTER (WHERE scheduled_arrival <= scheduled_departure)::text,
        '0 invalid scheduled timestamp pairs'
    FROM bookings.flights

    UNION ALL

    SELECT
        'source_actual_times_are_ordered',
        COUNT(*) FILTER (
            WHERE actual_arrival IS NOT NULL
                AND (actual_departure IS NULL OR actual_arrival <= actual_departure)
        ) = 0,
        COUNT(*) FILTER (
            WHERE actual_arrival IS NOT NULL
                AND (actual_departure IS NULL OR actual_arrival <= actual_departure)
        )::text,
        '0 invalid actual timestamp pairs'
    FROM bookings.flights

    UNION ALL

    SELECT
        'source_flight_statuses_are_known',
        COUNT(*) FILTER (
            WHERE status NOT IN (
                'Scheduled',
                'On Time',
                'Delayed',
                'Boarding',
                'Departed',
                'Arrived',
                'Cancelled'
            )
        ) = 0,
        COUNT(*) FILTER (
            WHERE status NOT IN (
                'Scheduled',
                'On Time',
                'Delayed',
                'Boarding',
                'Departed',
                'Arrived',
                'Cancelled'
            )
        )::text,
        '0 unknown status values'
    FROM bookings.flights

    UNION ALL

    SELECT
        'source_flights_match_one_route_version',
        COUNT(*) FILTER (WHERE routes.route_no IS NULL) = 0,
        COUNT(*) FILTER (WHERE routes.route_no IS NULL)::text,
        '0 unmatched flights'
    FROM bookings.flights AS flights
    LEFT JOIN bookings.routes AS routes
        ON routes.route_no = flights.route_no
        AND routes.validity @> flights.scheduled_departure
)
INSERT INTO ml.data_quality_results (
    check_name,
    passed,
    observed_value,
    expected_value
)
SELECT
    check_name,
    passed,
    observed_value,
    expected_value
FROM source_checks
RETURNING check_name, passed, observed_value, expected_value;
