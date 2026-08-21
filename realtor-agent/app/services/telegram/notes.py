"""Parse Damian / realtor Telegram notes into buy-box fields.

Deterministic regex only. Do not invent ARV, rent, or cap rate.
"""

from __future__ import annotations

import re
from decimal import Decimal

from app.services.matching.screening import normalize_property_type
from app.utilities.money import as_decimal, money_label

OPP_ID_RE = re.compile(r"OPP-\d{4}-\d+")
HOLD_RE = re.compile(
    r"buy\s*and\s*hold|held for a long time|long[- ]term rental|(?:not|no)\s+(?:for\s+)?flipp",
    re.I,
)
RENTAL_RE = re.compile(r"\brentals?\b", re.I)
STRETCH_RE = re.compile(r"very good deal|more expensive|different parameters", re.I)
NO_HOA_RE = re.compile(r"\bno\s+hoa\b|\bwithout\s+(?:an\s+)?hoa\b|\bhoa\s*(?:is\s+)?(?:not|no)\b", re.I)
ADDITIONAL_RE = re.compile(
    r"\badditional(?:\s+one)?\b|\bextra(?:\s+one)?\b|\bsecondary\b|"
    r"\bjust\s+(?:an\s+)?add(?:ed|itional)\b",
    re.I,
)
MAIN_RE = re.compile(
    r"\b(?:the\s+)?main\s+(?:one|box|search|criteria|buy\s*box)\b|"
    r"\bprimary\s+(?:one|box|search|criteria)\b",
    re.I,
)
LOW_PRIORITY_RE = re.compile(
    r"not a priority|no(?:t)?\s+priority|low(?:er)?\s+priority|"
    r"don'?t prioritize|do not prioritize|no rush",
    re.I,
)
ARV_PCT_RE = re.compile(
    r"(?P<n>\d{1,3}(?:\.\d+)?)\s*%\s*(?:of\s+)?(?:arv|after[\s-]?repair(?:\s+value)?|market(?:\s+value)?)"
    r"|(?:arv|after[\s-]?repair(?:\s+value)?|market(?:\s+value)?)\s*(?:of\s+|at\s+|is\s+)?"
    r"(?P<n2>\d{1,3}(?:\.\d+)?)\s*%",
    re.I,
)
TYPE_PATTERNS = (
    (re.compile(r"\bcondos?\b|\bcondominiums?\b", re.I), "condo"),
    (re.compile(r"\btown\s*-?houses?\b|\btownhomes?\b", re.I), "townhouse"),
    (re.compile(r"\bmulti[\s-]?famil|\bmf\b", re.I), "multi_family"),
    (re.compile(r"\bsingle[\s-]?famil|\bsfh\b|\bhouses?\b", re.I), "single_family"),
)
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
    property_types = _property_types(raw)
    max_price_pct_of_arv = _arv_pct(raw)
    hoa_required = False if NO_HOA_RE.search(raw) else None
    parsed = {
        "raw": raw,
        "min_price": min_price,
        "max_price": max_price,
        "buy_and_hold": buy_and_hold,
        "stretch_over_max": bool(STRETCH_RE.search(raw)),
        "property_types": property_types,
        "max_price_pct_of_arv": max_price_pct_of_arv,
        "hoa_required": hoa_required,
        "mentions_additional": bool(ADDITIONAL_RE.search(raw)),
        "mentions_main": bool(MAIN_RE.search(raw)),
        "low_priority": bool(LOW_PRIORITY_RE.search(raw)),
        "opportunity_id": extract_opportunity_id(raw),
    }
    parsed["has_criteria"] = any(
        [
            parsed["min_price"] is not None,
            parsed["max_price"] is not None,
            parsed["buy_and_hold"],
            parsed["stretch_over_max"],
            bool(parsed["property_types"]),
            parsed["max_price_pct_of_arv"] is not None,
            parsed["hoa_required"] is False,
            parsed["mentions_additional"],
            parsed["mentions_main"],
            parsed["low_priority"],
        ]
    )
    return parsed


def format_note_confirmation(applied: dict) -> str:
    lines = ["Got it. Buy box updated from your Telegram note."]
    ranking = bool(applied.get("main_box") or applied.get("additional_box") or applied.get("low_priority"))
    if applied.get("main_box"):
        lines.append(f"Main box: {applied['main_box']}.")
    min_price = applied.get("min_price")
    max_price = applied.get("max_price")
    if min_price is not None or max_price is not None:
        lines.append(f"Primary: {money_label(min_price)} min / {money_label(max_price)} max.")
    if applied.get("buy_and_hold"):
        lines.append("Strategy: buy-and-hold rentals, not flips.")
    if applied.get("additional_box"):
        extra = str(applied["additional_box"])
        if applied.get("low_priority"):
            lines.append(f"Additional box: {extra} — not a priority. I will not lead with this box.")
        else:
            lines.append(f"Additional box: {extra} (not the main box).")
    elif applied.get("low_priority"):
        lines.append("That additional box is not a priority. I will not lead with it.")
    types = applied.get("property_types") or []
    if types and not ranking:
        lines.append("Property types: " + ", ".join(types) + ".")
    pct = applied.get("max_price_pct_of_arv")
    if pct is not None and not ranking:
        lines.append(f"Max purchase: {float(pct) * 100:.0f}% of ARV. ARV is not invented.")
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
    search = applied.get("search") or {}
    if search:
        types = applied.get("property_types") or []
        kind = applied.get("main_box") or (", ".join(types) if types else "matching")
        if not search.get("connected"):
            lines.append(f"I'll check MLS for {kind} listings that pass this box.")
            lines.append("No MLS data connection yet — I cannot pull listings.")
        else:
            matched = int(search.get("matched") or 0)
            provider = search.get("provider") or "mls"
            lines.append(
                f"MLS search ({provider}, not Matrix): {matched} match"
                f"{'' if matched == 1 else 'es'}."
            )
            if matched:
                lines.append("Listing cards posted. Approve does not text investors.")
            else:
                lines.append("No listings in the current feed passed that box.")
    return "\n".join(lines)


def _property_types(text: str) -> list[str]:
    found: list[str] = []
    for pattern, name in TYPE_PATTERNS:
        if pattern.search(text) and name not in found:
            found.append(name)
    return found


def _arv_pct(text: str) -> Decimal | None:
    match = ARV_PCT_RE.search(text)
    if not match:
        return None
    raw = match.group("n") or match.group("n2")
    value = as_decimal(raw)
    if value is None:
        return None
    if value > 1:
        value = (value / Decimal("100")).quantize(Decimal("0.0001"))
    return value


def _to_price(number: str | None, thousand_suffix: str | None) -> Decimal | None:
    value = as_decimal(number)
    if value is None:
        return None
    if thousand_suffix:
        return value * Decimal("1000")
    return value
