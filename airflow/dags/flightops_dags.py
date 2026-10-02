"""Thin Airflow DAG definitions for FlightOps Sentinel."""

from __future__ import annotations

from datetime import UTC, datetime

from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import DAG, get_current_context

from flightops.pipeline import materialize_features, monitor_model_outcomes, validate_contracts
from flightops.scoring.batch import score_flights
from flightops.training.config import load_config
from flightops.training.experiment import TrainingExperiment

DEFAULT_ARGS = {"owner": "flightops", "retries": 0}


def _score() -> None:
    context = get_current_context()
    score_flights(context["data_interval_start"], context["data_interval_end"])


def _train() -> None:
    config = load_config("configs/training/logistic.yaml")
    experiment = TrainingExperiment(config)
    experiment.track(experiment.run())


with DAG(
    "validate_source_data",
    default_args=DEFAULT_ARGS,
    schedule="@daily",
    start_date=datetime(2025, 9, 1, tzinfo=UTC),
    catchup=False,
    tags=["flightops", "data-quality"],
) as validate_source_data:
    PythonOperator(task_id="run_contracts", python_callable=validate_contracts)

with DAG(
    "materialize_features",
    default_args=DEFAULT_ARGS,
    schedule=None,
    start_date=datetime(2025, 9, 1, tzinfo=UTC),
    catchup=False,
    tags=["flightops", "features"],
) as materialize_features_dag:
    PythonOperator(task_id="refresh_feature_mart", python_callable=materialize_features)

with DAG(
    "batch_score_flights",
    default_args=DEFAULT_ARGS,
    schedule="@daily",
    start_date=datetime(2025, 9, 1, tzinfo=UTC),
    catchup=False,
    tags=["flightops", "scoring"],
) as batch_score_flights:
    PythonOperator(
        task_id="score_approved_model",
        python_callable=_score,
    )

with DAG(
    "train_delay_model",
    default_args=DEFAULT_ARGS,
    schedule=None,
    start_date=datetime(2025, 9, 1, tzinfo=UTC),
    catchup=False,
    tags=["flightops", "training"],
) as train_delay_model:
    PythonOperator(task_id="train_candidate", python_callable=_train)

with DAG(
    "monitor_model_outcomes",
    default_args=DEFAULT_ARGS,
    schedule="@daily",
    start_date=datetime(2025, 9, 1, tzinfo=UTC),
    catchup=False,
    tags=["flightops", "monitoring"],
) as monitor_model_outcomes_dag:
    PythonOperator(task_id="count_matured_predictions", python_callable=monitor_model_outcomes)
