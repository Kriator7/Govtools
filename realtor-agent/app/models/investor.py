"""Investor CRM identity. Acquisition criteria live on InvestorCriteria, not here."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import PublicIdMixin, RealtorScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Investor(UUIDPrimaryKeyMixin, PublicIdMixin, RealtorScopedMixin, TimestampMixin, Base):
    __tablename__ = "investors"

    name: Mapped[str] = mapped_column(String(200))
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preferred_channel: Mapped[str] = mapped_column(String(32), default="sms")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    communication_permissions: Mapped[dict] = mapped_column(JSON, default=dict)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    import_source: Mapped[str | None] = mapped_column(String(80), nullable=True)

    realtor = relationship("Realtor", back_populates="investors")
    criteria_profiles = relationship(
        "InvestorCriteria", back_populates="investor", cascade="all, delete-orphan"
    )
    opportunities = relationship("Opportunity", back_populates="investor")
    transactions = relationship("Transaction", back_populates="investor")
