# Flight Delay Data Contract

## Purpose

This contract defines the source assumptions, staging record, and label used by FlightOps Sentinel. It is enforced by SQL checks stored in `sql/checks/` and recorded in `ml.data_quality_results`.

## Source Boundary

The source schema is `bookings`, which is read-only to the project role. The project writes only to `staging`, `analytics`, and `ml`.

Required source entities:

| Entity | Required fields |
| --- | --- |
| `bookings.flights` | `flight_id`, `route_no`, `status`, scheduled and actual departure/arrival timestamps |
| `bookings.routes` | `route_no`, `validity`, departure/arrival airport, aircraft, duration |

The flight-to-route join uses both `route_no` and `routes.validity @> flights.scheduled_departure`. Joining on route number alone is invalid because route records are versioned over time.

## Staging Record

`staging.flight_records` has one row per `flight_id` and contains the operational fields needed for future feature work:

- scheduled and actual departure/arrival timestamps;
- route and aircraft fields;
- source flight status, retained only for operational auditing;
- `source_loaded_at`.

All timestamps are `timestamptz` and retain the source database time zone semantics.

## Target Label

The label is available through `analytics.flight_delay_labels`:

```text
is_departure_delayed_15m =
actual_departure > scheduled_departure + 15 minutes
```

If `actual_departure` is null, the label is null. Cancelled and future scheduled flights are therefore not treated as negative examples.

## Leakage Rules

`actual_departure`, `actual_arrival`, and final operational `status` are retained in staging for label creation and auditing only. They are prohibited from model features under the T-24h prediction contract.

```text
feature_cutoff = scheduled_departure - 24 hours
```

The static source snapshot is evaluated in UTC. A later feature mart must calculate every historical aggregate using only records available at or before this cutoff.

## Commands

```powershell
.\scripts\apply-migrations.ps1
.\scripts\refresh-staging.ps1
.\scripts\run-data-contracts.ps1
```

The derived-field definitions are listed in the [data dictionary](data-dictionary.md).
