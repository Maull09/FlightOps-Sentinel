# Repository Instructions

## Engineering Principles

- I prefer stupid simple code instead of smart one.
- No need to create fallback and backward compatibility unless user asking to do so.

## Project Context

This repository contains FlightOps Sentinel, a production-oriented machine-learning system that predicts whether a scheduled flight will depart at least 15 minutes late.

## Working Conventions

- Keep the first implementation focused on the defined delay-risk use case.
- Prefer explicit, readable Python and SQL over clever abstractions.
- Treat all timestamps as timezone-aware.
- Prevent target leakage: features must be available at the configured prediction time.
- Use time-based data splits for model evaluation.
- Do not alter source data in the operational `bookings` schema; create derived data in project-owned schemas.
