from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from wellness_agent.models import (
    CRYPTO_KEYS,
    REQUIRED_CATEGORIES,
    InboxItemStatus,
    InboxSnapshot,
)

_DATA_PACKAGE = "wellness_agent.data"
_INBOX_FILE = "current_inbox.json"

REQUIRED_FIELDS = ("kind", "title", "copy", "inbox_note") + REQUIRED_CATEGORIES

CRYPTO_PHRASES = (
    "strait of hormuz",
    "btc threshold",
    "capital-regime",
    "macro liquidity",
    "geopolitical / market catalyst",
)


def _reject_crypto_mix(payload: dict) -> None:
    """Keep this agent Wellness-only. Crypto/macro catalyst belongs to a different bot."""
    mixed_keys = sorted(CRYPTO_KEYS.intersection(payload))
    if mixed_keys:
        raise ValueError(
            "TrueHold Wellness agent cannot include crypto/macro fields: "
            + ", ".join(mixed_keys)
        )
    blob = " ".join(str(value) for value in payload.values()).lower()
    for phrase in CRYPTO_PHRASES:
        if phrase in blob:
            raise ValueError(
                f"TrueHold Wellness agent cannot include crypto content ({phrase!r})"
            )


def _status_from_payload(name: str, payload: dict) -> InboxItemStatus:
    raw = payload.get(name)
    if not isinstance(raw, dict) or "new" not in raw or not raw.get("detail"):
        raise ValueError(f"Inbox snapshot is missing a reliable {name} status")
    return InboxItemStatus(new=bool(raw["new"]), detail=str(raw["detail"]))


def parse_inbox(payload: dict) -> InboxSnapshot:
    """Validate and build a complete inbox snapshot. All business categories are required."""
    _reject_crypto_mix(payload)
    missing = [key for key in REQUIRED_FIELDS if key not in payload or payload.get(key) in ("", None)]
    if missing:
        raise ValueError(f"Inbox snapshot is missing fields: {missing}")
    return InboxSnapshot(
        kind=payload["kind"],
        title=payload["title"],
        copy=payload["copy"],
        inbox_note=payload["inbox_note"],
        orders=_status_from_payload("orders", payload),
        payments=_status_from_payload("payments", payload),
        fulfillment=_status_from_payload("fulfillment", payload),
        shipping=_status_from_payload("shipping", payload),
        cancellations=_status_from_payload("cancellations", payload),
        peptides=_status_from_payload("peptides", payload),
        other_actionable=_status_from_payload("other_actionable", payload),
    )


@lru_cache(maxsize=1)
def load_current_inbox() -> InboxSnapshot:
    """Load the current Wellness inbox snapshot. All business categories are required."""
    payload = json.loads(
        resources.files(_DATA_PACKAGE).joinpath(_INBOX_FILE).read_text(encoding="utf-8")
    )
    return parse_inbox(payload)
