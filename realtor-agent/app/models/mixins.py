"""Shared SQLAlchemy mixins. realtor_id is required on major entities (data separation)."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class RealtorScopedMixin:
    realtor_id: Mapped[UUID] = mapped_column(ForeignKey("realtors.id"), index=True)


class PublicIdMixin:
    public_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
