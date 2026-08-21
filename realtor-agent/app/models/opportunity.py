"""A scored match between one listing and one investor criteria profile."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import OpportunityStatus
from app.models.mixins import PublicIdMixin, RealtorScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Opportunity(UUIDPrimaryKeyMixin, PublicIdMixin, RealtorScopedMixin, TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint(
            "listing_id",
            "investor_id",
            "criteria_id",
            "match_version",
            name="uq_opportunity_match_version",
        ),
    )

    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"), index=True)
    investor_id: Mapped[UUID] = mapped_column(ForeignKey("investors.id"), index=True)
    criteria_id: Mapped[UUID] = mapped_column(ForeignKey("investor_criteria.id"), index=True)
    transaction_id: Mapped[UUID | None] = mapped_column(nullable=True)

    score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    score_category: Mapped[str] = mapped_column(String(32))
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(64), default=OpportunityStatus.MATCH_DETECTED.value)
    match_version: Mapped[int] = mapped_column(Integer, default=1)
    listing_fingerprint: Mapped[str] = mapped_column(String(64), default="")

    rejection_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rejection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    snooze_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notified_investor_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    realtor = relationship("Realtor", back_populates="opportunities")
    listing = relationship("Listing", back_populates="opportunities")
    investor = relationship("Investor", back_populates="opportunities")
    criteria = relationship("InvestorCriteria", back_populates="opportunities")
