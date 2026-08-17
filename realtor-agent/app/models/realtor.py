"""Realtor identity. Credentials are referenced by Secret Manager name, never stored raw."""

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import PublicIdMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Realtor(UUIDPrimaryKeyMixin, PublicIdMixin, TimestampMixin, Base):
    __tablename__ = "realtors"

    name: Mapped[str] = mapped_column(String(200))
    brokerage: Mapped[str | None] = mapped_column(String(200), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    license_state: Mapped[str] = mapped_column(String(8), default="NV")
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    telegram_user_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Los_Angeles")
    mls_config_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    transaction_platform_config_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notification_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    investors = relationship("Investor", back_populates="realtor")
    listings = relationship("Listing", back_populates="realtor")
    opportunities = relationship("Opportunity", back_populates="realtor")
    transactions = relationship("Transaction", back_populates="realtor")
