from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


TRIGGER_TYPES = (
    "business",
    "order",
    "payment",
    "fulfillment",
    "shipping",
    "cancellation",
    "peptide",
    "manual",
)

REQUIRED_CATEGORIES = (
    "orders",
    "payments",
    "fulfillment",
    "shipping",
    "cancellations",
    "peptides",
    "other_actionable",
)

# Crypto/macro content belongs to the TrueHold crypto agent. Do not add it here.
CRYPTO_KEYS = frozenset(
    {"catalyst", "btc_threshold", "capital_regime", "macro_liquidity", "geopolitical_catalyst"}
)


@dataclass(frozen=True)
class InboxItemStatus:
    """One Wellness inbox category. Always present so the snapshot stays complete."""

    new: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InboxSnapshot:
    """Full TrueHold Wellness inbox snapshot attached to every Wellness alert."""

    kind: str
    title: str
    copy: str
    inbox_note: str
    orders: InboxItemStatus
    payments: InboxItemStatus
    fulfillment: InboxItemStatus
    shipping: InboxItemStatus
    cancellations: InboxItemStatus
    peptides: InboxItemStatus
    other_actionable: InboxItemStatus

    def categories(self) -> dict[str, InboxItemStatus]:
        return {
            "orders": self.orders,
            "payments": self.payments,
            "fulfillment": self.fulfillment,
            "shipping": self.shipping,
            "cancellations": self.cancellations,
            "peptides": self.peptides,
            "other_actionable": self.other_actionable,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "kind": self.kind,
            "title": self.title,
            "copy": self.copy,
            "inbox_note": self.inbox_note,
        }
        for name, status in self.categories().items():
            payload[name] = status.to_dict()
        return payload


@dataclass(frozen=True)
class AlertTrigger:
    type: str
    headline: str
    detail: str = ""

    def __post_init__(self) -> None:
        if self.type in CRYPTO_KEYS:
            raise ValueError("TrueHold Wellness agent does not send crypto/macro triggers")
        if self.type not in TRIGGER_TYPES:
            raise ValueError(f"Unknown trigger type: {self.type}")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class Alert:
    trigger: AlertTrigger
    inbox: InboxSnapshot
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "truehold-wellness-agent"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "agent": "truehold-wellness-agent",
            "trigger": self.trigger.to_dict(),
            "inbox": self.inbox.to_dict(),
        }
