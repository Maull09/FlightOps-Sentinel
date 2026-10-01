"""Reusable commands invoked by Airflow DAGs."""

from __future__ import annotations

import logging
from pathlib import Path

import psycopg

from flightops.database import database_connection_string

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)


def execute_sql(relative_path: str) -> None:
    """Execute one reviewed SQL file against the project database."""

    statement = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
    LOGGER.info("Executing SQL file: %s", relative_path)
    with psycopg.connect(database_connection_string()) as connection:
        connection.execute(statement)
        connection.commit()


def validate_contracts() -> None:
    """Run all contract SQL and fail when the newest result for a check is false."""

    for filename in (
        "001_source_data_contract.sql",
        "002_staging_label_contract.sql",
        "003_feature_mart_contract.sql",
    ):
        execute_sql(f"sql/checks/{filename}")
    with psycopg.connect(database_connection_string()) as connection:
        result = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT ON (check_name) passed
                FROM ml.data_quality_results
                ORDER BY check_name, checked_at DESC, id DESC
            ) AS latest_checks
            WHERE NOT passed;
            """
        ).fetchone()
    if result is None:
        raise RuntimeError("Data-contract summary query returned no result.")
    failed_count = result[0]
    if failed_count:
        raise RuntimeError(f"{failed_count} latest data-contract checks failed.")


def materialize_features() -> None:
    """Refresh project-owned staging, labels, and cutoff-safe features."""

    execute_sql("sql/staging/001_refresh_flight_records.sql")
    execute_sql("sql/ml/001_refresh_flight_delay_features.sql")


def monitor_model_outcomes() -> int:
    """Count predictions whose flight labels have matured for Airflow observability."""

    with psycopg.connect(database_connection_string()) as connection:
        result = connection.execute(
            """
            SELECT COUNT(*)
            FROM ml.flight_delay_predictions AS predictions
            JOIN ml.flight_delay_features AS features
                ON features.flight_id = predictions.flight_id
            WHERE features.is_departure_delayed_15m IS NOT NULL;
            """
        ).fetchone()
    if result is None:
        raise RuntimeError("Model-outcome query returned no result.")
    LOGGER.info("Matured prediction count: %s", result[0])
    return int(result[0])
