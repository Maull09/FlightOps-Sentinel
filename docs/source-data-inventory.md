# Source Data Inventory

This document records the local inspection of the Postgres Professional Airline Demo Database restored for FlightOps Sentinel.

## Dataset Snapshot

| Field | Value |
| --- | --- |
| Dataset version | `PostgresPro 2025-09-01 (1 year)` |
| Database snapshot time | `2026-11-01 00:00:00+00` |
| Database time zone | `Etc/UTC` |
| Scheduled-flight range | `2025-10-01 00:00:00+00` to `2026-10-30 23:50:00+00` |
| Flights | 69,710 |

The source is a static snapshot. Flights after the snapshot time are present as scheduled records but do not yet have actual outcomes. They are not labelled training examples. The actual-departure range is intentionally not treated as a fixed source contract because it depends on the source snapshot's completed-flight status.

## Flight Status Distribution

| Status | Count |
| --- | ---: |
| Arrived | 10,966 |
| Boarding | 4 |
| Cancelled | 121 |
| Delayed | 10 |
| Departed | 20 |
| On Time | 157 |
| Scheduled | 10,480 |

`status` is a source operational field, but it is not a model feature for the T-24h prediction contract because it can reflect post-cutoff operational state.

## Source Tables

| Table | Local total size |
| --- | ---: |
| `bookings.airplanes_data` | 32 kB |
| `bookings.airports_data` | 1.4 MB |
| `bookings.boarding_passes` | 361 MB |
| `bookings.bookings` | 92 MB |
| `bookings.flights` | 2.8 MB |
| `bookings.routes` | 344 kB |
| `bookings.seats` | 176 kB |
| `bookings.segments` | 436 MB |
| `bookings.tickets` | 470 MB |

## Access Boundary

The local project role `flightops_app` has:

- `SELECT` access to the `bookings` schema;
- no `INSERT` access to `bookings.flights`;
- ownership of the project schemas `staging`, `analytics`, and `ml`.

This boundary keeps the restored operational source immutable from the project's perspective.
