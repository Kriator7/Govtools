"""Deterministic money helpers. Do not use AI for threshold comparisons."""

from decimal import Decimal, InvalidOperation


def as_decimal(value: object | None) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        if not cleaned:
            return None
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def money_label(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.0f}"
