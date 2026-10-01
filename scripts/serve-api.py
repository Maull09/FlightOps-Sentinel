"""Run the local FlightOps Sentinel API."""

from __future__ import annotations

import os

import uvicorn
from dotenv import load_dotenv


def main() -> None:
    load_dotenv(override=True)
    uvicorn.run(
        "flightops.api.app:app",
        host=os.environ["API_HOST"],
        port=int(os.environ["API_PORT"]),
    )


if __name__ == "__main__":
    main()
