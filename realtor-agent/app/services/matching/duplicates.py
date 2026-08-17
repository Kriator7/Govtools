"""Duplicate / re-alert rules. Re-alert only on material listing changes."""

from decimal import Decimal
from typing import Any

from app.utilities.hashing import fingerprint

MATERIAL_FIELDS = (
    "asking_price",
    "listing_status",
    "seller_financing",
    "foreclosure",
    "short_sale",
    "assumable_loan",
    "occupancy_status",
    "hoa_monthly",
    "estimated_rent",
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    return value


def material_fields(listing: Any) -> dict:
    return {field: _json_safe(getattr(listing, field, None)) for field in MATERIAL_FIELDS}


def listing_fingerprint(listing: Any) -> str:
    return fingerprint(material_fields(listing))


def is_material_change(previous: dict | None, current: Any) -> bool:
    if not previous:
        return True
    return fingerprint(previous) != listing_fingerprint(current)
