"""Idempotent batch scoring using the explicitly approved MLflow model alias."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import pandas as pd
import psycopg

from flightops.database import database_connection_string
from flightops.scoring.model import MODEL_NAME, load_approved_model
from flightops.scoring.policy import risk_level
from flightops.training.config import INPUT_FEATURES


def score_flights(execution_start: datetime, execution_end: datetime) -> int:
    """Score rows whose T-24h cutoff falls in an Airflow data interval."""

    if execution_start.utcoffset() is None or execution_end.utcoffset() is None:
        raise ValueError("Scoring intervals must use timezone-aware timestamps.")
    if execution_start >= execution_end:
        raise ValueError("Scoring interval start must precede its end.")
    model, model_version = load_approved_model()
    with psycopg.connect(database_connection_string()) as connection:
        rows = _load_scoring_features(connection, execution_start, execution_end)
        if rows.empty:
            return 0
        probabilities = model.predict_proba(rows[INPUT_FEATURES])[:, 1]
        predictions = [
            (
                int(flight_id),
                feature_cutoff,
                MODEL_NAME,
                model_version,
                float(probability),
                risk_level(float(probability)),
            )
            for flight_id, feature_cutoff, probability in zip(
                rows["flight_id"], rows["feature_cutoff"], probabilities, strict=True
            )
        ]
        return _store_predictions(connection, predictions)


def _load_scoring_features(
    connection: psycopg.Connection,
    execution_start: datetime,
    execution_end: datetime,
) -> pd.DataFrame:
    query = f"""
        SELECT flight_id, feature_cutoff, {", ".join(INPUT_FEATURES)}
        FROM ml.flight_delay_features
        WHERE feature_cutoff >= %s
          AND feature_cutoff < %s
        ORDER BY feature_cutoff, flight_id;
    """
    return pd.read_sql(query, connection, params=(execution_start, execution_end))


def _store_predictions(
    connection: psycopg.Connection, predictions: Sequence[tuple[object, ...]]
) -> int:
    statement = """
        INSERT INTO ml.flight_delay_predictions (
            flight_id, feature_cutoff, model_name, model_version,
            delay_risk_probability, risk_level
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (flight_id, feature_cutoff, model_name, model_version) DO NOTHING;
    """
    with connection.cursor() as cursor:
        cursor.executemany(statement, predictions)
        inserted_count = cursor.rowcount
    return inserted_count
