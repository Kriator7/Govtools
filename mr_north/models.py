from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

AGENT_ID = "mr-north"

TRIGGER_TYPES = (
    "geopolitical_catalyst",
    "btc_threshold",
    "capital_regime",
    "macro_liquidity",
    "manual",
)

# TrueHold Wellness is a separate, already-working agent. Mr North must not send its content.
FOREIGN_KEYS = frozenset({"business", "wellness", "inbox", "peptide", "order"})


@dataclass(frozen=True)
class CatalystBriefing:
    """Geopolitical / market catalyst payload attached to every Mr North alert."""

    kind: str
    title: str
    summary: str
    why_it_matters: str
    crypto: str
    watch_next: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class AlertTrigger:
    type: str
    headline: str
    detail: str = ""

    def __post_init__(self) -> None:
        if self.type not in TRIGGER_TYPES:
            raise ValueError(f"Unknown Mr North trigger type: {self.type}")
        if self.type in FOREIGN_KEYS:
            raise ValueError("Mr North does not send TrueHold Wellness triggers")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class Alert:
    trigger: AlertTrigger
    catalyst: CatalystBriefing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = AGENT_ID

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "agent": AGENT_ID,
            "trigger": self.trigger.to_dict(),
            "catalyst": self.catalyst.to_dict(),
        }
