"""Inbound realtor document-packet replies. Secrets from email are never stored raw."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base
from app.models.enums import PacketStatus
from app.models.mixins import PublicIdMixin, TimestampMixin, UUIDPrimaryKeyMixin


class RealtorPacket(UUIDPrimaryKeyMixin, PublicIdMixin, TimestampMixin, Base):
    __tablename__ = "realtor_packets"
    __table_args__ = (
        UniqueConstraint("message_id", "packet_number", name="uq_realtor_packet_message_number"),
    )

    realtor_id: Mapped[UUID | None] = mapped_column(ForeignKey("realtors.id"), nullable=True, index=True)
    packet_number: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default=PacketStatus.RECEIVED.value)
    message_id: Mapped[str] = mapped_column(String(500), index=True)
    account: Mapped[str | None] = mapped_column(String(200), nullable=True)
    from_header: Mapped[str | None] = mapped_column(String(500), nullable=True)
    to_header: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    missing_fields: Mapped[list] = mapped_column(JSON, default=list)
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    apply_result: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    realtor = relationship("Realtor", back_populates="packets")
