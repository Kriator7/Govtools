from decimal import Decimal

from app.models.investor_criteria import PIRATES_IG_STRICT_FIELDS
from app.services.matching.engine import MatchingEngine
from app.services.matching.screening import PIRATES_MAX_PRICE_PCT_OF_ARV, screen_listing
from tests.unit.test_matching import _criteria, _listing


def _pirates(**listing_overrides):
    defaults = dict(
        asking_price=Decimal("360000"),
        arv=Decimal("400000"),
        city="Las Vegas",
        property_type="single_family",
        hoa_monthly=Decimal("0"),
        mls_listing_id="Example-001",
        street_address="Example property",
    )
    defaults.update(listing_overrides)
    listing = _listing(**defaults)
    criteria = _criteria(
        name="Pirates IG LLC acquisition",
        min_price=None,
        max_price=None,
        zip_codes=[],
        cities=["Las Vegas", "North Las Vegas", "Henderson"],
        min_bedrooms=None,
        min_bathrooms=None,
        min_sqft=None,
        year_built_min=None,
        hoa_required=False,
        max_hoa=None,
        min_estimated_rent=None,
        max_price_pct_of_arv=PIRATES_MAX_PRICE_PCT_OF_ARV,
        strict_fields=list(PIRATES_IG_STRICT_FIELDS),
    )
    return listing, criteria


def test_example_001_passes_at_90_percent_arv():
    listing, criteria = _pirates()
    screening = screen_listing(listing, criteria)
    assert screening["price_divided_by_arv"] == "90.0%"
    assert screening["max_allowed_price"] == "$360,000"
    assert screening["property_type_pass"] == "PASS"
    assert screening["area_pass"] == "PASS"
    assert screening["hoa_pass"] == "PASS"
    assert screening["price_pass"] == "PASS"
    result = MatchingEngine().evaluate(listing, criteria)
    assert result.matched
    assert result.needs_arv is False
    assert any("90.0% of ARV" in reason for reason in result.reasons)


def test_price_above_90_percent_arv_fails():
    listing, criteria = _pirates(asking_price=Decimal("360001"))
    result = MatchingEngine().evaluate(listing, criteria)
    assert not result.matched
    assert any("max allowed" in item.lower() for item in result.failures)


def test_hoa_rejects():
    listing, criteria = _pirates(hoa_monthly=Decimal("185"))
    result = MatchingEngine().evaluate(listing, criteria)
    assert not result.matched
    assert any("HOA" in item for item in result.failures)


def test_wrong_city_rejects():
    listing, criteria = _pirates(city="Reno")
    result = MatchingEngine().evaluate(listing, criteria)
    assert not result.matched


def test_single_family_home_alias_passes():
    listing, criteria = _pirates(property_type="Single-family home")
    result = MatchingEngine().evaluate(listing, criteria)
    assert result.matched


def test_missing_arv_does_not_invent_value():
    listing, criteria = _pirates(arv=None)
    result = MatchingEngine().evaluate(listing, criteria)
    assert result.matched
    assert result.needs_arv is True
    assert result.screening["price_pass"] == "NEEDS_ARV"
    assert result.category == "needs_arv"


def test_no_bed_bath_year_minimums():
    listing, criteria = _pirates(bedrooms=1, bathrooms=1, sqft=700, year_built=1955)
    result = MatchingEngine().evaluate(listing, criteria)
    assert result.matched
