"""Connection configuration for the project-owned PostgreSQL data."""

from __future__ import annotations

import os

from psycopg.conninfo import make_conninfo


def database_connection_string() -> str:
    required = (
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_PROJECT_USER",
        "POSTGRES_PROJECT_PASSWORD",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing PostgreSQL configuration: {', '.join(missing)}")
    return make_conninfo(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname="demo",
        user=os.environ["POSTGRES_PROJECT_USER"],
        password=os.environ["POSTGRES_PROJECT_PASSWORD"],
    )
