import runpy
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.mark.parametrize(
    "script", ["train-baseline.py", "train-candidates.py", "validate-training-data.py"]
)
def test_training_scripts_import_without_running_jobs(
    script: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = MagicMock(side_effect=AssertionError("Import must not open a database connection"))
    monkeypatch.setattr("psycopg.connect", connection)
    namespace = runpy.run_path(str(Path("scripts") / script), run_name="entrypoint_import_test")

    assert callable(namespace["main"])
    connection.assert_not_called()
