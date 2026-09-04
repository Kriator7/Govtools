"""Public, non-MLS seller-lead drafts for PirateEye.

Do not scrape authenticated MLS websites. These drafts come from public RSS
and documented government pages only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class OpenLeadDraft:
    source: str
    title: str
    summary: str
    url: str
    fingerprint: str
    city: str | None = None
    state: str = "NV"
    zip_code: str | None = None
    person_name: str | None = None
    street_address: str | None = None
    asking_price: Decimal | None = None
    published_at: datetime | None = None
    property_type: str = "single_family"
    review_only: bool = False
    assessor_url: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @property
    def can_become_listing(self) -> bool:
        return (
            not self.review_only
            and bool(self.street_address)
            and self.asking_price is not None
            and bool(self.city)
        )


class OpenLeadProvider(ABC):
    name: str = "open"
    review_only: bool = False

    @abstractmethod
    def search(self) -> list[OpenLeadDraft]:
        raise NotImplementedError

    def health(self) -> tuple[str, str]:
        try:
            rows = self.search()
            return ("ok", f"{self.name} returned {len(rows)} public items")
        except Exception as exc:  # noqa: BLE001
            return ("error", str(exc))
