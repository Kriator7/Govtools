"""Parse Damian / realtor Telegram notes into buy-box fields.

Deterministic regex only. Do not invent ARV, rent, or cap rate.
"""

from __future__ import annotations

import re
from decimal import Decimal

from app.utilities.money import as_decimal, money_label

OPP_ID_RE = re.compile(r"OPP-\d{4}-\d+")
HOLD_RE = re.compile(
    r"buy\s*and\s*hold|held for a long time|long[- ]term rental|(?:not|no)\s+(?:for\s+)?flipp",
    re.I,
)
RENTAL_RE = re.compile(r"\brentals?\b", re.I)
STRETCH_RE = re.compile(r"very good deal|more expensive|different parameters", re.I)
BOUND_BEFORE = re.compile(
    r"(?P<n>\$?\d{1,3}(?:,\d{3})+|\d{2,4})\s*(?P<k>k)?\s*(?P<kind>min(?:imum)?|max(?:imum)?)",
    re.I,
)
BOUND_AFTER = re.compile(
    r"(?P<kind>min(?:imum)?|max(?:imum)?)(?:\s+price)?(?:\s+(?:of|is|go))?\s*"
    r"(?P<n>\$?\d{1,3}(?:,\d{3})+|\d{2,4})\s*(?P<k>k)?",
    re.I,
)


def extract_opportunity_id(*texts: str | None) -> str | None:
    for text in texts:
        match = OPP_ID_RE.search(str(text or ""))
        if match:
            return match.group(0)
    return None


def parse_realtor_note(text: str) -> dict:
    raw = str(text or "").strip()
    min_price = None
    max_price = None
    for match in list(BOUND_BEFORE.finditer(raw)) + list(BOUND_AFTER.finditer(raw)):
        kind = match.group("kind").lower()
        price = _to_price(match.group("n"), match.group("k"))
        if price is None:
            continue
        if kind.startswith("min") and min_price is None:
            min_price = price
        elif kind.startswith("max") and max_price is None:
            max_price = price
    buy_and_hold = bool(HOLD_RE.search(raw))
    if RENTAL_RE.search(raw) and ("long" in raw.lower() or buy_and_hold):
        buy_and_hold = True
    parsed = {
        "raw": raw,
        "min_price": min_price,
        "max_price": max_price,
        "buy_and_hold": buy_and_hold,
        "stretch_over_max": bool(STRETCH_RE.search(raw)),
        "opportunity_id": extract_opportunity_id(raw),
    }
    parsed["has_criteria"] = any(
        [
            parsed["min_price"] is not None,
            parsed["max_price"] is not None,
            parsed["buy_and_hold"],
            parsed["stretch_over_max"],
        ]
    )
    return parsed


def format_note_confirmation(applied: dict) -> str:
    lines = ["Got it. Buy box updated from your Telegram note."]
    min_price = applied.get("min_price")
    max_price = applied.get("max_price")
    if min_price is not None or max_price is not None:
        lines.append(f"Primary: {money_label(min_price)} min / {money_label(max_price)} max.")
    if applied.get("buy_and_hold"):
        lines.append("Strategy: buy-and-hold rentals, not flips.")
    if applied.get("stretch"):
        stretch = applied["stretch"]
        pct = float(stretch.get("max_price_pct_of_arv") or 0) * 100
        lines.append(
            "Stretch: over the primary max only if it is a very good deal "
            f"(Price ÷ ARV ≤ {pct:.0f}%). Different parameters from the core box."
        )
    rejected = applied.get("rejected") or []
    if rejected:
        lines.append("Removed from the primary queue: " + ", ".join(rejected) + ".")
    investor = applied.get("investor")
    if investor:
        lines.append(f"Investor: {investor}. Relays stay on.")
    return "\n".join(lines)


def _to_price(number: str | None, thousand_suffix: str | None) -> Decimal | None:
    value = as_decimal(number)
    if value is None:
        return None
    if thousand_suffix:
        return value * Decimal("1000")
    return value
