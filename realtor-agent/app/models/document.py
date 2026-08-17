"""Generated documents. Executed files are never overwritten."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import DocumentStatus, DocumentType
from app.models.mixins import PublicIdMixin, RealtorScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, PublicIdMixin, RealtorScopedMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    transaction_id: Mapped[UUID] = mapped_column(ForeignKey("transactions.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(64), default=DocumentType.PURCHASE_AGREEMENT.value)
    template_name: Mapped[str] = mapped_column(String(120))
    template_version: Mapped[str] = mapped_column(String(32))
    jurisdiction: Mapped[str] = mapped_column(String(16), default="NV")
    status: Mapped[str] = mapped_column(String(40), default=DocumentStatus.DRAFT.value)
    review_required: Mapped[bool] = mapped_column(Boolean, default=True)

    source_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generated_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generated_by: Mapped[str] = mapped_column(String(80), default="system")
    reviewed_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    review_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    field_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    transaction = relationship("Transaction", back_populates="documents")
