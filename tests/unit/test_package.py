"""Smoke tests for the application package."""


def test_package_imports() -> None:
    import flightops

    assert flightops.__doc__ is not None
