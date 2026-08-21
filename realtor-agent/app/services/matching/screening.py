"""Pirates IG LLC Property Screening calculations.

Mirrors Damian's Numbers columns:
A–G inputs, H Price÷ARV, I Max Allowed Price, J Type Pass, K Area Pass.
Never invent ARV. If ARV is missing, price cannot PASS.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.utilities.money import money_label

PIRATES_CITIES = ("Las Vegas", "North Las Vegas", "Henderson")
PIRATES_MAX_PRICE_PCT_OF_ARV = Decimal("0.90")

PROPERTY_TYPE_ALIASES = {
    "single_family": "single_family",
    "single_family_home": "single_family",
    "single_family_house": "single_family",
    "sfh": "single_family",
    "house": "single_family",
    "home": "single_family",
    "multi_family": "multi_family",
    "multifamily": "multi_family",
    "condo": "condo",
    "condos": "condo",
    "condominium": "condo",
    "condominiums": "condo",
    "townhouse": "townhouse",
    "townhouses": "townhouse",
    "townhome": "townhouse",
    "townhomes": "townhouse",
    "land": "land",
}


def normalize_property_type(value: Any) -> str:
    raw = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return PROPERTY_TYPE_ALIASES.get(raw, raw)


def has_hoa(listing: Any) -> bool:
    hoa = getattr(listing, "hoa_monthly", None)
    return hoa is not None and Decimal(str(hoa)) > 0


def max_allowed_price(arv: Decimal, pct: Decimal = PIRATES_MAX_PRICE_PCT_OF_ARV) -> Decimal:
    return (arv * pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def price_divided_by_arv(price: Decimal, arv: Decimal) -> Decimal:
    if arv <= 0:
        raise ValueError("ARV must be greater than zero")
    return (price / arv).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def screen_listing(listing: Any, criteria: Any) -> dict:
    """Return the same pass/fail fields Damian's screening tab calculates."""
    cities = [str(c) for c in (getattr(criteria, "cities", None) or [])]
    types = [normalize_property_type(item) for item in (getattr(criteria, "property_types", None) or [])]
    pct = getattr(criteria, "max_price_pct_of_arv", None) or PIRATES_MAX_PRICE_PCT_OF_ARV
    pct = Decimal(str(pct))
    price = Decimal(str(listing.asking_price))
    arv = getattr(listing, "arv", None)
    arv_value = Decimal(str(arv)) if arv is not None else None

    type_pass = not types or normalize_property_type(listing.property_type) in types
    area_pass = not cities or _norm_city(listing.city) in {_norm_city(c) for c in cities}
    hoa_forbidden = getattr(criteria, "hoa_required", None) is False
    hoa_pass = (not has_hoa(listing)) if hoa_forbidden else True

    needs_arv = arv_value is None and getattr(criteria, "max_price_pct_of_arv", None) is not None
    max_price = max_allowed_price(arv_value, pct) if arv_value is not None else None
    ratio = price_divided_by_arv(price, arv_value) if arv_value is not None else None
    price_pass = None if needs_arv else (max_price is not None and price <= max_price)

    return {
        "property_id": getattr(listing, "mls_listing_id", None),
        "address": getattr(listing, "street_address", None),
        "city": listing.city,
        "property_type": listing.property_type,
        "hoa": "Yes" if has_hoa(listing) else "No",
        "purchase_price": money_label(price),
        "arv": money_label(arv_value) if arv_value is not None else None,
        "price_divided_by_arv": f"{float(ratio) * 100:.1f}%" if ratio is not None else None,
        "max_allowed_price": money_label(max_price) if max_price is not None else None,
        "property_type_pass": "PASS" if type_pass else "FAIL",
        "area_pass": "PASS" if area_pass else "FAIL",
        "hoa_pass": "PASS" if hoa_pass else "FAIL",
        "price_pass": "NEEDS_ARV" if needs_arv else ("PASS" if price_pass else "FAIL"),
        "needs_arv": needs_arv,
        "max_price_pct_of_arv": float(pct),
    }


def _norm_city(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
