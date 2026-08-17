"""Lightweight analytics events so a later dashboard can query without re-deriving history."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import UUIDPrimaryKeyMixin, utcnow


class AnalyticsEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "analytics_events"

    realtor_id: Mapped[UUID] = mapped_column(ForeignKey("realtors.id"), index=True)
    event_name: Mapped[str] = mapped_column(String(80), index=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
