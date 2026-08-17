"""Normalized listing plus raw MLS payload for troubleshooting."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import PublicIdMixin, RealtorScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Listing(UUIDPrimaryKeyMixin, PublicIdMixin, RealtorScopedMixin, TimestampMixin, Base):
    __tablename__ = "listings"
    __table_args__ = (UniqueConstraint("realtor_id", "mls_listing_id", name="uq_listing_realtor_mls"),)

    mls_listing_id: Mapped[str] = mapped_column(String(80), index=True)
    listing_version: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str] = mapped_column(String(80), default="mock")

    street_address: Mapped[str] = mapped_column(String(300))
    city: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(8), default="NV")
    zip_code: Mapped[str] = mapped_column(String(16), index=True)
    neighborhood: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)

    asking_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    property_type: Mapped[str] = mapped_column(String(40))
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lot_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_on_market: Mapped[int | None] = mapped_column(Integer, nullable=True)
    listing_status: Mapped[str] = mapped_column(String(40), default="active")
    listing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    hoa_monthly: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    taxes_annual: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_rent: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    cap_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    grm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    occupancy_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    seller_financing: Mapped[bool] = mapped_column(default=False)
    foreclosure: Mapped[bool] = mapped_column(default=False)
    short_sale: Mapped[bool] = mapped_column(default=False)
    assumable_loan: Mapped[bool] = mapped_column(default=False)
    repair_estimate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    listing_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photos: Mapped[list] = mapped_column(JSON, default=list)
    price_history: Mapped[list] = mapped_column(JSON, default=list)
    status_history: Mapped[list] = mapped_column(JSON, default=list)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    material_fingerprint: Mapped[str] = mapped_column(String(64), default="")

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    realtor = relationship("Realtor", back_populates="listings")
    opportunities = relationship("Opportunity", back_populates="listing")
    transactions = relationship("Transaction", back_populates="listing")
