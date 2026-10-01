from flightops.scoring.policy import risk_level


def test_risk_levels_use_documented_thresholds() -> None:
    assert risk_level(0.02) == "low"
    assert risk_level(0.03) == "medium"
    assert risk_level(0.06) == "high"
