from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from truehold.crypto_agent.models import WELLNESS_KEYS, CatalystBriefing

_DATA_PACKAGE = "truehold.crypto_agent.data"
_CATALYST_FILE = "current_catalyst.json"

REQUIRED_FIELDS = (
    "kind",
    "title",
    "summary",
    "why_it_matters",
    "crypto",
    "watch_next",
)

WELLNESS_PHRASES = (
    "truehold wellness",
    "peptide",
    "fulfillment",
    "connected inbox",
    "cancellation/refund",
)


def _reject_wellness_mix(payload: dict) -> None:
    """Keep this agent crypto-only. Wellness/business inbox belongs to a different bot."""
    mixed_keys = sorted(WELLNESS_KEYS.intersection(payload))
    if mixed_keys:
        raise ValueError(
            "TrueHold crypto agent cannot include Wellness/business fields: "
            + ", ".join(mixed_keys)
        )
    blob = " ".join(str(value) for value in payload.values()).lower()
    for phrase in WELLNESS_PHRASES:
        if phrase in blob:
            raise ValueError(
                f"TrueHold crypto agent cannot include Wellness content ({phrase!r})"
            )


@lru_cache(maxsize=1)
def load_current_catalyst() -> CatalystBriefing:
    """Load the current geopolitical / market catalyst briefing shipped with the crypto agent."""
    payload = json.loads(
        resources.files(_DATA_PACKAGE).joinpath(_CATALYST_FILE).read_text(encoding="utf-8")
    )
    _reject_wellness_mix(payload)
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
