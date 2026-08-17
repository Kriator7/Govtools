"""Authorized MLS provider interface.

Do not scrape authenticated MLS webpages unless the MLS provider explicitly
permits it. Only use API/feed access supplied by the realtor or brokerage.

If a vendor schema is unavailable, implement a mock first. Do not invent a
vendor-specific RESO/Spark/Bridge payload.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class NormalizedListingDraft:
    mls_listing_id: str
    street_address: str
    city: str
    state: str
    zip_code: str
    asking_price: Decimal
    property_type: str
    neighborhood: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    previous_price: Decimal | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    sqft: int | None = None
    lot_sqft: int | None = None
    year_built: int | None = None
    days_on_market: int | None = None
    listing_status: str = "active"
    listing_date: datetime | None = None
    hoa_monthly: Decimal | None = None
    taxes_annual: Decimal | None = None
    estimated_rent: Decimal | None = None
    cap_rate: Decimal | None = None
    grm: Decimal | None = None
    occupancy_status: str | None = None
    seller_financing: bool = False
    foreclosure: bool = False
    short_sale: bool = False
    assumable_loan: bool = False
    repair_estimate: Decimal | None = None
    remarks: str | None = None
    agent_remarks: str | None = None
    listing_url: str | None = None
    photos: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)
    provider: str = "mock"


class MLSProvider(ABC):
    name: str = "base"

    @abstractmethod
    def authenticate(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_new_listings(self, since: datetime | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_updated_listings(self, since: datetime | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_listing(self, mls_listing_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def normalize_listing(self, raw: dict[str, Any]) -> NormalizedListingDraft:
        raise NotImplementedError

    def health(self) -> tuple[str, str]:
        try:
            ok = self.authenticate()
            return ("ok", "authenticated") if ok else ("error", "authentication failed")
        except Exception as exc:  # noqa: BLE001
            return ("error", str(exc))
