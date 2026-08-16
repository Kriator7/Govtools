from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from mr_north.models import FOREIGN_KEYS, CatalystBriefing

_DATA_PACKAGE = "mr_north.data"
_CATALYST_FILE = "current_catalyst.json"

REQUIRED_FIELDS = (
    "kind",
    "title",
    "summary",
    "why_it_matters",
    "crypto",
    "watch_next",
)

# Phrases that belong to the separate TrueHold Wellness agent, not Mr North.
FOREIGN_PHRASES = (
    "truehold wellness",
    "peptide",
    "fulfillment",
    "connected inbox",
    "cancellation/refund",
)


def _reject_foreign_mix(payload: dict) -> None:
    """Mr North is crypto/macro only. Do not attach TrueHold Wellness inbox content."""
    mixed_keys = sorted(FOREIGN_KEYS.intersection(payload))
    if mixed_keys:
        raise ValueError("Mr North cannot include TrueHold Wellness fields: " + ", ".join(mixed_keys))
    blob = " ".join(str(value) for value in payload.values()).lower()
    for phrase in FOREIGN_PHRASES:
        if phrase in blob:
            raise ValueError(f"Mr North cannot include TrueHold Wellness content ({phrase!r})")


@lru_cache(maxsize=1)
def load_current_catalyst() -> CatalystBriefing:
    """Load the current geopolitical / market catalyst briefing shipped with Mr North."""
    payload = json.loads(
        resources.files(_DATA_PACKAGE).joinpath(_CATALYST_FILE).read_text(encoding="utf-8")
    )
    _reject_foreign_mix(payload)
    missing = [key for key in REQUIRED_FIELDS if not payload.get(key)]
    if missing:
        raise ValueError(f"Catalyst briefing is missing fields: {missing}")
    return CatalystBriefing(
        kind=payload["kind"],
        title=payload["title"],
        summary=payload["summary"],
        why_it_matters=payload["why_it_matters"],
        crypto=payload["crypto"],
        watch_next=payload["watch_next"],
    )
