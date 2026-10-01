# Flight Delay Feature Contract

## Prediction Time

The initial model predicts at T-24h:

```text
feature_cutoff = scheduled_departure - 24 hours
```

The feature mart has one row per `flight_id` in `ml.flight_delay_features`.

## Static Flight Features

The following fields are available from the scheduled flight and the route valid at its scheduled departure:

- local departure hour, day of week, and month;
- route number;
- origin and destination airport;
- airplane code;
- scheduled duration in minutes.

Local calendar features use the origin airport time zone from `bookings.airports_data`.

## Historical Features

Each historical delay aggregate uses only flights satisfying:

```text
history.actual_departure <= target.feature_cutoff
```

The aggregates are calculated by route, origin airport, aircraft code, destination airport, and route × local departure hour. They expose a completed-flight count and a delay rate. A missing rate is preserved as null when no completed history exists; imputation is a model-training decision, not a SQL fallback. The route-hour aggregate derives the hour with the relevant origin airport timezone and is still restricted to completed flights at or before the target cutoff.

## Booking Dynamics and Schedule Congestion

Booking features use only reservations whose `book_date` is at or before the feature cutoff. They include ticket counts booked in the prior 7 and 30 days and mean ticket lead time. These counts are subsets of the existing cumulative booking-demand features, so a value of zero is valid for a flight with no recent reservations.

Schedule-congestion features count other scheduled departures at the origin and scheduled arrivals at the destination in the two-hour window centered on the target flight's scheduled time. They use only scheduled fields, never actual times or flight status. The static DemoDB snapshot has no schedule-publication or amendment timestamps; FlightOps therefore treats its scheduled records as published by T-24h. A production source must provide an as-of schedule feed or publication timestamp before using these features.

## Forbidden Features

The feature mart must not include:

- `actual_departure`;
- `actual_arrival`;
- `flight_status`;
- any field derived from a flight event after the cutoff.

These values remain available in staging only for label calculation and auditing.

## Verification

`sql/checks/003_feature_mart_contract.sql` validates row grain, fixed cutoff, label parity, absence of forbidden columns, and cutoff-safe route history on a deterministic sample of flight IDs.

## Local Development Refresh Policy

Refreshing `ml.flight_delay_features` explicitly truncates both
`ml.flight_delay_predictions` and `ml.flight_delay_features`. Predictions are a cache tied to
the prior feature snapshot, so they must not survive a full local feature rebuild. This policy
only affects project-owned `ml` tables and never mutates the operational `bookings` schema.
