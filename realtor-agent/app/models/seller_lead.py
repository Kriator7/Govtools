"""Public-source seller leads. Obituaries stay review-only; FSBO/HUD may become listings."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import PublicIdMixin, RealtorScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SellerLead(UUIDPrimaryKeyMixin, PublicIdMixin, RealtorScopedMixin, TimestampMixin, Base):
    __tablename__ = "seller_leads"
    __table_args__ = (UniqueConstraint("realtor_id", "fingerprint", name="uq_seller_lead_realtor_fingerprint"),)

    source: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str] = mapped_column(String(8), default="NV")
    zip_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    person_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    street_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    asking_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_only: Mapped[bool] = mapped_column(Boolean, default=False)
    assessor_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    listing_id: Mapped[UUID | None] = mapped_column(ForeignKey("listings.id"), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)

    realtor = relationship("Realtor", back_populates="seller_leads")
    listing = relationship("Listing")
