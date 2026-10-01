"""Train and register the model family selected by one YAML configuration."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from flightops.training.config import load_config
from flightops.training.experiment import TrainingExperiment


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(override=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", default="configs/training/logistic.yaml")
    args = parser.parse_args()
    pipeline = TrainingExperiment(load_config(args.config))
    result = pipeline.run()
    run_id = pipeline.track(result)
    print(f"MLflow run: {run_id}; model family: {result.family}")


if __name__ == "__main__":
    main()
