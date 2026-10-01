WITH feature_checks AS (
    SELECT
        'feature_mart_row_count_matches_staging' AS check_name,
        (SELECT COUNT(*) FROM ml.flight_delay_features) = (SELECT COUNT(*) FROM staging.flight_records) AS passed,
        (SELECT COUNT(*) FROM ml.flight_delay_features)::text AS observed_value,
        (SELECT COUNT(*) FROM staging.flight_records)::text AS expected_value

    UNION ALL

    SELECT
        'feature_mart_has_extended_cutoff_safe_history_columns',
        COUNT(*) = 4,
        COUNT(*)::text,
        '4 extended history columns'
    FROM information_schema.columns
    WHERE table_schema = 'ml'
        AND table_name = 'flight_delay_features'
        AND column_name IN (
            'historical_destination_completed_count',
            'historical_destination_delay_rate',
            'historical_route_hour_completed_count',
            'historical_route_hour_delay_rate'
        )

    UNION ALL

    SELECT
        'feature_mart_has_cutoff_safe_demand_and_schedule_columns',
        COUNT(*) = 5,
        COUNT(*)::text,
        '5 booking-dynamics and schedule-congestion columns'
    FROM information_schema.columns
    WHERE table_schema = 'ml'
        AND table_name = 'flight_delay_features'
        AND column_name IN (
            'booked_ticket_count_last_7d',
            'booked_ticket_count_last_30d',
            'booked_ticket_average_lead_time_hours',
            'origin_scheduled_departures_2h',
            'destination_scheduled_arrivals_2h'
        )

    UNION ALL

    SELECT
        'feature_mart_cutoff_is_t24h',
        COUNT(*) FILTER (
            WHERE feature_cutoff <> scheduled_departure - INTERVAL '24 hours'
        ) = 0,
        COUNT(*) FILTER (
            WHERE feature_cutoff <> scheduled_departure - INTERVAL '24 hours'
        )::text,
        '0 rows with an invalid feature cutoff'
    FROM ml.flight_delay_features

    UNION ALL

    SELECT
        'feature_mart_has_no_forbidden_feature_columns',
        COUNT(*) = 0,
        COUNT(*)::text,
        '0 forbidden columns'
    FROM information_schema.columns
    WHERE table_schema = 'ml'
        AND table_name = 'flight_delay_features'
        AND column_name IN ('actual_departure', 'actual_arrival', 'flight_status')

    UNION ALL

    SELECT
        'feature_mart_label_matches_contract',
        COUNT(*) FILTER (
            WHERE features.is_departure_delayed_15m IS DISTINCT FROM labels.is_departure_delayed_15m
        ) = 0,
        COUNT(*) FILTER (
            WHERE features.is_departure_delayed_15m IS DISTINCT FROM labels.is_departure_delayed_15m
        )::text,
        '0 label mismatches'
    FROM ml.flight_delay_features AS features
    JOIN analytics.flight_delay_labels AS labels
        ON labels.flight_id = features.flight_id

    UNION ALL

    SELECT
        'feature_mart_sampled_route_history_is_cutoff_safe',
        COUNT(*) FILTER (
            WHERE features.historical_route_completed_count <> recalculated.completed_count
                OR features.historical_route_delay_rate IS DISTINCT FROM recalculated.delay_rate
        ) = 0,
        COUNT(*) FILTER (
            WHERE features.historical_route_completed_count <> recalculated.completed_count
                OR features.historical_route_delay_rate IS DISTINCT FROM recalculated.delay_rate
        )::text,
        '0 sampled route-history mismatches'
    FROM ml.flight_delay_features AS features
    JOIN LATERAL (
        SELECT
            COUNT(*)::integer AS completed_count,
            AVG((history.actual_departure > history.scheduled_departure + INTERVAL '15 minutes')::integer)::double precision
                AS delay_rate
        FROM staging.flight_records AS history
        WHERE history.route_no = features.route_no
            AND history.actual_departure <= features.feature_cutoff
    ) AS recalculated ON true
    WHERE MOD(features.flight_id, 997) = 0
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
FROM feature_checks
RETURNING check_name, passed, observed_value, expected_value;
