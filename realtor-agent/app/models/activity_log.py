"""User-facing chronological timeline for opportunities and transactions."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import ActorType
from app.models.mixins import RealtorScopedMixin, UUIDPrimaryKeyMixin, utcnow


class ActivityLog(UUIDPrimaryKeyMixin, RealtorScopedMixin, Base):
    __tablename__ = "activity_logs"

    opportunity_id: Mapped[UUID | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True, index=True)
    transaction_id: Mapped[UUID | None] = mapped_column(ForeignKey("transactions.id"), nullable=True, index=True)
    listing_id: Mapped[UUID | None] = mapped_column(ForeignKey("listings.id"), nullable=True)
    investor_id: Mapped[UUID | None] = mapped_column(ForeignKey("investors.id"), nullable=True)

    event_type: Mapped[str] = mapped_column(String(80), index=True)
    message: Mapped[str] = mapped_column(Text)
    actor_type: Mapped[str] = mapped_column(String(32), default=ActorType.SYSTEM.value)
    actor_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    transaction = relationship("Transaction", back_populates="activity_logs")
