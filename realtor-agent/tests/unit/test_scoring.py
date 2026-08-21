from decimal import Decimal

from app.services.scoring.engine import score_category, weighted_score


def test_score_categories():
    assert score_category(94) == "excellent"
    assert score_category(84) == "strong"
    assert score_category(72) == "possible"
    assert score_category(69) == "below_threshold"


def test_weighted_score_floors_at_zero():
    assert weighted_score([40, 40, 40]) == Decimal("0")
    assert weighted_score([5]) == Decimal("95")
