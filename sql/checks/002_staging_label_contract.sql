WITH staging_checks AS (
    SELECT
        'staging_row_count_matches_source' AS check_name,
        (SELECT COUNT(*) FROM staging.flight_records) = (SELECT COUNT(*) FROM bookings.flights) AS passed,
        (SELECT COUNT(*) FROM staging.flight_records)::text AS observed_value,
        (SELECT COUNT(*) FROM bookings.flights)::text AS expected_value

    UNION ALL

    SELECT
        'delay_label_is_null_without_actual_departure',
        COUNT(*) FILTER (
            WHERE actual_departure IS NULL
                AND is_departure_delayed_15m IS NOT NULL
        ) = 0,
        COUNT(*) FILTER (
            WHERE actual_departure IS NULL
                AND is_departure_delayed_15m IS NOT NULL
        )::text,
        '0 labelled rows without actual departure'
    FROM analytics.flight_delay_labels

    UNION ALL

    SELECT
        'delay_label_matches_15_minute_definition',
        COUNT(*) FILTER (
            WHERE actual_departure IS NOT NULL
                AND is_departure_delayed_15m IS DISTINCT FROM (
                    actual_departure > scheduled_departure + INTERVAL '15 minutes'
                )
        ) = 0,
        COUNT(*) FILTER (
            WHERE actual_departure IS NOT NULL
                AND is_departure_delayed_15m IS DISTINCT FROM (
                    actual_departure > scheduled_departure + INTERVAL '15 minutes'
                )
        )::text,
        '0 label-definition mismatches'
    FROM analytics.flight_delay_labels
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
FROM staging_checks
RETURNING check_name, passed, observed_value, expected_value;
