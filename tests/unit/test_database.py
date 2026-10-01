import pytest
from psycopg.conninfo import conninfo_to_dict

from flightops.database import database_connection_string


def test_connection_configuration_quotes_special_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_PROJECT_USER": "flightops_app",
        "POSTGRES_PROJECT_PASSWORD": "space quote' backslash\\ password",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    connection = conninfo_to_dict(database_connection_string())
    assert connection["password"] == values["POSTGRES_PROJECT_PASSWORD"]
    assert connection["dbname"] == "demo"


def test_missing_configuration_names_the_missing_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTGRES_PROJECT_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="POSTGRES_PROJECT_PASSWORD"):
        database_connection_string()
