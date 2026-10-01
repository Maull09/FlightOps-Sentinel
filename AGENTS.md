# Repository Instructions

## Engineering Principles

- I prefer stupid simple code instead of smart one.
- No need to create fallback and backward compatibility unless user asking to do so.
- Use indentation and naming conventions that are consistent with the rest of the codebase.
- Make code readable and maintainable, even if it means writing more lines of code.
- Avoid over-engineering and unnecessary abstractions.
- Avoid premature optimization; focus on clarity and correctness first.
- Edit todo.md to track progress and document decisions.
- Edit README.md to provide a high-level overview of the project.
- Edit docs/ to provide detailed instructions for running and maintaining the system, including setup, configuration, and troubleshooting.

## Project Context

This repository contains FlightOps Sentinel, a production-oriented machine-learning system that predicts whether a scheduled flight will depart at least 15 minutes late.

## Working Conventions

- Keep the first implementation focused on the defined delay-risk use case.
- Prefer explicit, readable Python and SQL over clever abstractions.
- Treat all timestamps as timezone-aware.
- Prevent target leakage: features must be available at the configured prediction time.
- Use time-based data splits for model evaluation.
- Do not alter source data in the operational `bookings` schema; create derived data in project-owned schemas.

## Skill Usage

Use `clean-code` skill and `karpathy-guidelines` for code writing, reviewing and editing