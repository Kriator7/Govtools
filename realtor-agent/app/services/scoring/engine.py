"""Configurable opportunity scoring. Financial thresholds stay deterministic."""

from decimal import Decimal

from app.config import scoring_weights_defaults


def score_category(score: Decimal | float | int) -> str:
    value = float(score)
    if value >= 90:
        return "excellent"
    if value >= 80:
        return "strong"
    if value >= 70:
        return "possible"
    return "below_threshold"


def weighted_score(deductions: list[float], weights: dict[str, float] | None = None) -> Decimal:
    _ = weights or scoring_weights_defaults()
    total = max(0.0, 100.0 - sum(deductions))
    return Decimal(str(round(total, 2)))
