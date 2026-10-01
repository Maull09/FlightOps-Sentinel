"""Train and evaluate the chronological logistic-regression baseline."""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from flightops.training.config import load_config
from flightops.training.experiment import TrainingExperiment


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(override=True)
    experiment = TrainingExperiment(load_config("configs/training/logistic.yaml"))
    run_id = experiment.track(experiment.run())
    print(f"MLflow run: {run_id}")


if __name__ == "__main__":
    main()
