"""Inbound and outbound messages attached to an opportunity and/or transaction."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import CommunicationDirection, DeliveryStatus
from app.models.mixins import PublicIdMixin, RealtorScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Communication(UUIDPrimaryKeyMixin, PublicIdMixin, RealtorScopedMixin, TimestampMixin, Base):
    __tablename__ = "communications"

    opportunity_id: Mapped[UUID | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True, index=True)
    transaction_id: Mapped[UUID | None] = mapped_column(ForeignKey("transactions.id"), nullable=True, index=True)
    investor_id: Mapped[UUID | None] = mapped_column(ForeignKey("investors.id"), nullable=True, index=True)

    channel: Mapped[str] = mapped_column(String(32))
    template: Mapped[str | None] = mapped_column(String(80), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), default=CommunicationDirection.OUTBOUND.value)
    recipient: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=DeliveryStatus.QUEUED.value)
    provider: Mapped[str] = mapped_column(String(40), default="mock")
    provider_message_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_value: Mapped[str | None] = mapped_column(String(32), nullable=True)

    transaction = relationship("Transaction", back_populates="communications")
