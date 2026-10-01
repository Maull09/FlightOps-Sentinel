# Data Dictionary

## `ml.training_runs`

Grain: one row per MLflow run ID. After migration 013, `candidate_beats_baseline` records the comparison decision; `baseline_test_metrics` stores comparator ROC-AUC/PR-AUC; `baseline_name` identifies the comparator (`plain_logistic` for new runs, `NULL` for unidentified legacy runs). `split_boundaries` records each window's scheduled timestamp range; `row_counts` records total/train/validation/test rows. The remaining fields identify the registered model version, test metrics, and UTC creation timestamp.

## `staging.flight_records`

Grain: one row per scheduled `flight_id`.

| Column | Type | Description | Feature eligibility at T-24h |
| --- | --- | --- | --- |
| `flight_id` | integer | Source flight identifier. | Identifier only |
| `route_no` | text | Source flight route number. | Allowed |
| `flight_status` | text | Current/final source operational status. | Prohibited |
| `scheduled_departure` | timestamptz | Planned departure timestamp. | Allowed |
| `scheduled_arrival` | timestamptz | Planned arrival timestamp. | Allowed |
| `actual_departure` | timestamptz | Observed departure timestamp. | Prohibited; label only |
| `actual_arrival` | timestamptz | Observed arrival timestamp. | Prohibited |
| `departure_airport` | char(3) | Origin airport from the valid route version. | Allowed |
| `arrival_airport` | char(3) | Destination airport from the valid route version. | Allowed |
| `airplane_code` | char(3) | Scheduled aircraft code from the valid route version. | Allowed |
| `scheduled_duration` | interval | Scheduled route duration. | Allowed |
| `source_loaded_at` | timestamptz | Time this project loaded the source row. | Operational metadata only |

## `analytics.flight_delay_labels`

Grain: one row per `flight_id` from `staging.flight_records`.

| Column | Type | Description |
| --- | --- | --- |
| `flight_id` | integer | Source flight identifier. |
| `scheduled_departure` | timestamptz | Planned departure timestamp. |
| `actual_departure` | timestamptz | Observed departure timestamp used to calculate the target. |
| `is_departure_delayed_15m` | boolean nullable | `true` when actual departure is more than 15 minutes after schedule; `false` when actual departure exists and is not late; `null` when no actual departure is available. |

## `ml.data_quality_results`

Grain: one result per contract check execution.

| Column | Type | Description |
| --- | --- | --- |
| `id` | bigint | Generated result identifier. |
| `checked_at` | timestamptz | Time at which the check executed. |
| `check_name` | text | Stable identifier for the contract check. |
| `passed` | boolean | Whether the observed value met its expectation. |
| `observed_value` | text | Measured value emitted by the check. |
| `expected_value` | text | Expected value or rule. |

## `ml.flight_delay_features`

Grain: one row per `flight_id` at the fixed T-24h cutoff.

| Column group | Columns | Description |
| --- | --- | --- |
| Identity and timing | `flight_id`, `feature_cutoff`, `scheduled_departure`, `materialized_at` | Identifies the feature row and its prediction contract. |
| Label | `is_departure_delayed_15m` | Nullable training target; never an inference input. |
| Calendar | `scheduled_departure_hour`, `scheduled_departure_day_of_week`, `scheduled_departure_month` | Local origin-airport calendar features. |
| Scheduled flight | `route_no`, `departure_airport`, `arrival_airport`, `airplane_code`, `scheduled_duration_minutes` | Information known from schedule and valid route definition. |
| Route history | `historical_route_completed_count`, `historical_route_delay_rate` | Completed route outcomes available by cutoff. |
| Origin history | `historical_origin_completed_count`, `historical_origin_delay_rate` | Completed origin-airport outcomes available by cutoff. |
| Aircraft history | `historical_aircraft_completed_count`, `historical_aircraft_delay_rate` | Completed aircraft outcomes available by cutoff. |
| Booking dynamics | `booked_ticket_count`, `booked_revenue`, `aircraft_seat_capacity`, `booked_load_factor`, `booked_ticket_count_last_7d`, `booked_ticket_count_last_30d`, `booked_ticket_average_lead_time_hours` | Reservation demand available by the T-24h cutoff; recent counts use only reservations booked in the respective preceding window. |
| Schedule congestion | `origin_scheduled_departures_2h`, `destination_scheduled_arrivals_2h` | Counts of other scheduled movements in the two-hour window centered on the flight's scheduled departure or arrival. Requires a published-as-of-cutoff schedule assumption. |
