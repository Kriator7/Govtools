from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel


class ListingCreate(ORMModel):
    mls_listing_id: str
    street_address: str
    city: str
    state: str = "NV"
    zip_code: str
    neighborhood: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    asking_price: Decimal
    previous_price: Decimal | None = None
    arv: Decimal | None = None
    property_type: str
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
    photos: list[str] = Field(default_factory=list)
    raw_payload: dict = Field(default_factory=dict)
    provider: str = "mock"


class ListingRead(ListingCreate):
    id: UUID
    public_id: str
    realtor_id: UUID
    listing_version: int
    first_seen_at: datetime
    last_seen_at: datetime
    material_fingerprint: str
