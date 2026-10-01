"""Validate the labelled feature dataset before a training run."""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from flightops.training.config import load_config
from flightops.training.data import TrainingData


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", default="configs/training/logistic.yaml")
    args = parser.parse_args()
    TrainingData(load_config(args.config)).load()
    print("Training data validation passed.")


if __name__ == "__main__":
    main()
