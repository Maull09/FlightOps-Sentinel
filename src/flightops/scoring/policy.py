"""Provisional operational risk bands shared by API and batch scoring."""

MEDIUM_RISK_THRESHOLD = 0.03
HIGH_RISK_THRESHOLD = 0.06


def risk_level(probability: float) -> str:
    if probability >= HIGH_RISK_THRESHOLD:
        return "high"
    if probability >= MEDIUM_RISK_THRESHOLD:
        return "medium"
    return "low"
