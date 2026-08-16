from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from truehold.crypto_agent.models import CatalystBriefing

_DATA_PACKAGE = "truehold.crypto_agent.data"
_CATALYST_FILE = "current_catalyst.json"


@lru_cache(maxsize=1)
def load_current_catalyst() -> CatalystBriefing:
    """Load the current geopolitical / market catalyst briefing shipped with the agent."""
    payload = json.loads(
        resources.files(_DATA_PACKAGE).joinpath(_CATALYST_FILE).read_text(encoding="utf-8")
    )
    required = (
        "kind",
        "title",
        "summary",
        "why_it_matters",
        "crypto",
        "business",
        "watch_next",
    )
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise ValueError(f"Catalyst briefing is missing fields: {missing}")
    return CatalystBriefing(
        kind=payload["kind"],
        title=payload["title"],
        summary=payload["summary"],
        why_it_matters=payload["why_it_matters"],
        crypto=payload["crypto"],
        business=payload["business"],
        watch_next=payload["watch_next"],
    )
