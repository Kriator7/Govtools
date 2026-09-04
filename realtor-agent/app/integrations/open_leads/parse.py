"""Parse names, prices, and street lines from public RSS titles."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.integrations.open_leads.market import city_from_text

_PRICE_RE = re.compile(r"\$\s*([\d,]+(?:\.\d{1,2})?)")
_ADDRESS_RE = re.compile(
    r"\b(\d{1,6}\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+){0,4}\s+"
    r"(?:St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Rd|Road|Ln|Lane|Way|Ct|Court|Cir|Circle|Pl|Place|Ter|Terrace|Pkwy|Parkway|Hwy|Highway)\.?)\b",
    re.I,
)
_OBIT_NAME_RES = (
    re.compile(r"^obituary\s+(?:for\s+)?(?P<name>[A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){1,4})\b", re.I),
    re.compile(
        r"^(?P<name>[A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){1,4})\s+(?:obituary|passed away|dies|died)\b",
        re.I,
    ),
)


def asking_price_from_text(text: str) -> Decimal | None:
    match = _PRICE_RE.search(text or "")
    if not match:
        return None
    try:
        return Decimal(match.group(1).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def street_from_text(text: str) -> str | None:
    match = _ADDRESS_RE.search(text or "")
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip(" ,.-")


def person_from_obituary_title(title: str) -> str | None:
    blob = (title or "").strip()
    for pattern in _OBIT_NAME_RES:
        match = pattern.search(blob)
        if match:
            name = re.sub(r"\s+", " ", match.group("name")).strip(" ,.-")
            if name.lower() not in {"las vegas", "clark county"}:
                return name
    return None


def place_fields(text: str) -> tuple[str | None, str | None, str | None]:
    city = city_from_text(text)
    street = street_from_text(text)
    price = asking_price_from_text(text)
    return city, street, str(price) if price is not None else None
