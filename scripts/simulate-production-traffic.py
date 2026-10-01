"""Send controlled, production-like traffic to the local prediction API."""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import psycopg
from dotenv import load_dotenv

from flightops.database import database_connection_string


@dataclass(frozen=True)
class RequestResult:
    status_code: int
    latency_seconds: float


def eligible_flight_ids(limit: int) -> list[int]:
    query = """
        SELECT flight_id
        FROM ml.flight_delay_features
        WHERE feature_cutoff <= now()
          AND scheduled_departure > now()
        ORDER BY scheduled_departure, flight_id
        LIMIT %s;
    """
    with psycopg.connect(database_connection_string()) as connection:
        rows = connection.execute(query, (limit,)).fetchall()
    return [int(row[0]) for row in rows]


def request_prediction(api_url: str, flight_id: int) -> RequestResult:
    started = perf_counter()
    url = f"{api_url}/v1/predictions/flight-delay?flight_id={flight_id}"
    try:
        with urlopen(Request(url, method="POST"), timeout=30) as response:
            response.read()
            status_code = response.status
    except HTTPError as error:
        error.read()
        status_code = error.code
    except URLError as error:
        raise RuntimeError(f"API request failed: {error.reason}") from error
    return RequestResult(status_code=status_code, latency_seconds=perf_counter() - started)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
    return ordered[index]


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=120)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--error-rate", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.requests <= 0 or args.concurrency <= 0 or not 0 <= args.error_rate < 1:
        raise ValueError("requests/concurrency must be positive and error-rate must be in [0, 1).")

    api_url = f"http://localhost:{os.environ.get('API_PORT', '8000')}"
    flight_ids = eligible_flight_ids(args.requests)
    if not flight_ids:
        raise RuntimeError("No flights are eligible for a T-24h API prediction.")

    random_generator = random.Random(args.seed)
    traffic = [
        -1 if random_generator.random() < args.error_rate else flight_ids[index % len(flight_ids)]
        for index in range(args.requests)
    ]
    started = perf_counter()
    results: list[RequestResult] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(request_prediction, api_url, flight_id) for flight_id in traffic]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed = perf_counter() - started

    latencies = [result.latency_seconds for result in results]
    status_counts: dict[str, int] = {}
    for result in results:
        key = str(result.status_code)
        status_counts[key] = status_counts.get(key, 0) + 1
    summary = {
        "requests": len(results),
        "concurrency": args.concurrency,
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(len(results) / elapsed, 3),
        "status_counts": status_counts,
        "latency_ms": {
            "mean": round(statistics.mean(latencies) * 1000, 2),
            "p50": round(percentile(latencies, 0.50) * 1000, 2),
            "p95": round(percentile(latencies, 0.95) * 1000, 2),
            "max": round(max(latencies) * 1000, 2),
        },
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
