"""Fixture MLS feed for local demonstration. Replace with an authorized adapter later."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT
from app.integrations.mls.base import MLSProvider, NormalizedListingDraft


class MockMLSProvider(MLSProvider):
    name = "mock"

    def __init__(self, fixture_path: Path | None = None) -> None:
        self.fixture_path = fixture_path or (PROJECT_ROOT / "data" / "imports" / "sample_listings.json")
        self._authenticated = False

    def authenticate(self) -> bool:
        self._authenticated = self.fixture_path.exists()
        return self._authenticated

    def _load(self) -> list[dict[str, Any]]:
        if not self.fixture_path.exists():
            return []
        return json.loads(self.fixture_path.read_text(encoding="utf-8"))

    def fetch_new_listings(self, since: datetime | None = None) -> list[dict[str, Any]]:
        return list(self._load())

    def fetch_updated_listings(self, since: datetime | None = None) -> list[dict[str, Any]]:
        return list(self._load())

    def get_listing(self, mls_listing_id: str) -> dict[str, Any] | None:
        for raw in self._load():
            if str(raw.get("mls_id") or raw.get("mls_listing_id")) == str(mls_listing_id):
                return raw
        return None

    def normalize_listing(self, raw: dict[str, Any]) -> NormalizedListingDraft:
        listing_date = raw.get("listing_date")
        parsed_date = None
        if listing_date:
            parsed_date = datetime.fromisoformat(str(listing_date).replace("Z", "+00:00"))
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        return NormalizedListingDraft(
            mls_listing_id=str(raw.get("mls_id") or raw.get("mls_listing_id")),
            street_address=str(raw["street_address"]),
            city=str(raw["city"]),
            state=str(raw.get("state") or "NV"),
            zip_code=str(raw["zip_code"]),
            neighborhood=raw.get("neighborhood"),
            latitude=raw.get("latitude"),
            longitude=raw.get("longitude"),
            asking_price=Decimal(str(raw["asking_price"])),
            previous_price=Decimal(str(raw["previous_price"])) if raw.get("previous_price") else None,
            property_type=str(raw.get("property_type") or "single_family"),
            bedrooms=raw.get("bedrooms"),
            bathrooms=raw.get("bathrooms"),
            sqft=raw.get("sqft"),
            lot_sqft=raw.get("lot_sqft"),
            year_built=raw.get("year_built"),
            days_on_market=raw.get("days_on_market"),
            listing_status=str(raw.get("listing_status") or "active"),
            listing_date=parsed_date,
            hoa_monthly=Decimal(str(raw["hoa_monthly"])) if raw.get("hoa_monthly") is not None else None,
            taxes_annual=Decimal(str(raw["taxes_annual"])) if raw.get("taxes_annual") is not None else None,
            estimated_rent=Decimal(str(raw["estimated_rent"])) if raw.get("estimated_rent") is not None else None,
            cap_rate=Decimal(str(raw["cap_rate"])) if raw.get("cap_rate") is not None else None,
            grm=Decimal(str(raw["grm"])) if raw.get("grm") is not None else None,
            occupancy_status=raw.get("occupancy_status"),
            seller_financing=bool(raw.get("seller_financing", False)),
            foreclosure=bool(raw.get("foreclosure", False)),
            short_sale=bool(raw.get("short_sale", False)),
            assumable_loan=bool(raw.get("assumable_loan", False)),
            repair_estimate=Decimal(str(raw["repair_estimate"])) if raw.get("repair_estimate") is not None else None,
            remarks=raw.get("remarks"),
            agent_remarks=raw.get("agent_remarks"),
            listing_url=raw.get("listing_url"),
            photos=list(raw.get("photos") or []),
            raw_payload=raw,
            provider=self.name,
        )
