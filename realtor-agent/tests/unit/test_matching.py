from decimal import Decimal
from types import SimpleNamespace

from app.models.investor_criteria import DEFAULT_STRICT_FIELDS, InvestorCriteria
from app.services.matching.engine import MatchingEngine


def _listing(**overrides):
    data = dict(
        asking_price=Decimal("420000"),
        zip_code="89123",
        city="Las Vegas",
        neighborhood="Silverado Ranch",
        property_type="single_family",
        bedrooms=4,
        bathrooms=3,
        sqft=2150,
        lot_sqft=6000,
        year_built=1981,
        hoa_monthly=Decimal("0"),
        days_on_market=10,
        previous_price=Decimal("439000"),
        estimated_rent=Decimal("2400"),
        cap_rate=Decimal("0.067"),
        grm=Decimal("14.8"),
        occupancy_status="vacant",
        seller_financing=False,
        foreclosure=False,
        short_sale=False,
        assumable_loan=False,
        repair_estimate=Decimal("15000"),
        arv=None,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _criteria(**overrides):
    data = dict(
        name="LV SFH",
        min_price=Decimal("200000"),
        max_price=Decimal("450000"),
        max_purchase_price=None,
        zip_codes=["89123", "89119", "89120"],
        cities=["Las Vegas"],
        neighborhoods=[],
        property_types=["single_family"],
        min_bedrooms=3,
        min_bathrooms=2,
        min_sqft=1500,
        max_sqft=None,
        min_lot_sqft=None,
        year_built_min=1990,
        year_built_max=None,
        hoa_required=False,
        max_hoa=Decimal("250"),
        max_dom=None,
        require_price_reduction=False,
        min_estimated_rent=Decimal("2000"),
        min_cap_rate=None,
        max_grm=None,
        max_repair_estimate=None,
        occupancy_statuses=[],
        seller_financing_preferred=False,
        foreclosure_preferred=False,
        short_sale_preferred=False,
        assumable_loan_preferred=False,
        exclusion_rules=[],
        strict_fields=list(DEFAULT_STRICT_FIELDS),
        max_price_pct_of_arv=None,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_price_and_zip_and_beds_pass():
    result = MatchingEngine().evaluate(_listing(), _criteria())
    assert result.matched
    assert result.score >= Decimal("90")
    assert any("below" in reason.lower() or "maximum" in reason.lower() for reason in result.reasons)
    assert any("ZIP" in reason for reason in result.reasons)
    assert any("bedrooms" in reason for reason in result.reasons)


def test_strict_price_failure():
    result = MatchingEngine().evaluate(_listing(asking_price=Decimal("500000")), _criteria())
    assert not result.matched
    assert result.failures


def test_year_built_preference_is_issue_not_reject():
    result = MatchingEngine().evaluate(_listing(year_built=1981), _criteria(year_built_min=1990))
    assert result.matched
    assert result.issues
    assert any("1981" in issue for issue in result.issues)


def test_exclusion_rule_rejects():
    criteria = _criteria(exclusion_rules=[{"field": "zip_code", "operator": "eq", "value": "89123", "reason": "Excluded ZIP"}])
    result = MatchingEngine().evaluate(_listing(), criteria)
    assert not result.matched
    assert "Excluded ZIP" in result.failures
