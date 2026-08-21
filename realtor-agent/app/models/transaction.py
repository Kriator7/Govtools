"""Transaction is the spine of the system. All later work attaches here."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import TransactionStatus
from app.models.mixins import PublicIdMixin, RealtorScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Transaction(UUIDPrimaryKeyMixin, PublicIdMixin, RealtorScopedMixin, TimestampMixin, Base):
    __tablename__ = "transactions"

    opportunity_id: Mapped[UUID] = mapped_column(ForeignKey("opportunities.id"), index=True)
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"), index=True)
    investor_id: Mapped[UUID] = mapped_column(ForeignKey("investors.id"), index=True)
    criteria_id: Mapped[UUID] = mapped_column(ForeignKey("investor_criteria.id"), index=True)

    status: Mapped[str] = mapped_column(String(64), default=TransactionStatus.INVESTOR_INTERESTED.value)
    offer_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    financing_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    earnest_money: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    requested_closing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    buyer_legal_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    contingencies: Mapped[list] = mapped_column(JSON, default=list)
    dates: Mapped[dict] = mapped_column(JSON, default=dict)
    approvals: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    realtor = relationship("Realtor", back_populates="transactions")
    listing = relationship("Listing", back_populates="transactions")
    investor = relationship("Investor", back_populates="transactions")
    documents = relationship("Document", back_populates="transaction")
    communications = relationship("Communication", back_populates="transaction")
    activity_logs = relationship("ActivityLog", back_populates="transaction")
