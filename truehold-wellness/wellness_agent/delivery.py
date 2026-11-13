"""Standing TrueHold Wellness local-delivery rules. Application code only.

Merchandise subtotals are supplied by the caller (invoice CLI, confirmation call).
This module never invents SKU prices. College 10% is a separate discount.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

CENTS = Decimal("0.01")
LOCAL_DELIVERY_FEE = Decimal("20.00")
FREE_DELIVERY_THRESHOLD = Decimal("250.00")
LOCAL_DELIVERY_METHODS = frozenset({"prep", "delivery", "local"})
NO_LOCAL_DELIVERY_METHODS = frozenset({"pickup", "ship", "shipping"})

POLICY = (
    "Local Las Vegas delivery is $20. Merchandise of $250.00 or more includes "
    "free local delivery — two vials usually does it. Pickup has no delivery fee. "
    "Dry-vial shipping is quoted on the confirmation call — it is not this $20 local fee."
)

HELP = (
    "Local Las Vegas delivery is $20; orders of $250 or more include free delivery "
    "(two vials usually does it). Pickup is free."
)

INVOICE_SMALL_PRINT = (
    "Small print, big save: local Las Vegas delivery is $20. Spend $250 or more "
    "and we cover that ride — two vials usually does it. Pickup is free. "
    "Dry-vial shipping is quoted on the confirmation call."
)

TELEGRAM_SMALL_PRINT = (
    "<i>Local delivery $20 · free at $250+ · two vials usually does it</i>"
)

STAFF_DELIVERY_LINE = (
    "Local delivery: $20.00 unless merchandise is $250.00 or more (then $0.00). "
    "Apply on the invoice from the confirmed merchandise amount. Do not invent SKU prices."
)


def money(value: Any) -> Decimal:
    """USD to the cent. Callers pass the merchandise amount; this does not invent it."""
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def format_usd(value: Any) -> str:
    return f"${money(value):,.2f}"


def qualifies_for_free_delivery(merchandise_subtotal: Any) -> bool:
    """True when merchandise is $250.00 or more (standing 'over $250' rule)."""
    return money(merchandise_subtotal) >= FREE_DELIVERY_THRESHOLD


def delivery_charge(*, merchandise_subtotal: Any, fulfillment: str) -> Decimal:
    """$20 local Las Vegas delivery, or $0 when the order qualifies or is not local delivery.

    Pickup and dry-vial shipping do not use this $20 fee. Shipping is quoted on the call.
    """
    method = str(fulfillment or "delivery").strip().lower()
    if method in NO_LOCAL_DELIVERY_METHODS:
        return money(0)
    if method not in LOCAL_DELIVERY_METHODS:
        method = "delivery"
    if qualifies_for_free_delivery(merchandise_subtotal):
        return money(0)
    return LOCAL_DELIVERY_FEE


def customer_delivery_note(fulfillment: str) -> str:
    """Short Telegram HTML for confirmations. Empty for dry-vial shipping (fee not this $20)."""
    method = str(fulfillment or "prep").strip().lower()
    if method in NO_LOCAL_DELIVERY_METHODS and method != "pickup":
        return ""
    if method == "pickup":
        return "<i>Pickup has no delivery fee. Local delivery is $20, free at $250+.</i>"
    return TELEGRAM_SMALL_PRINT
