from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.enums import TransactionStatus
from app.schemas.common import ORMModel


class TransactionCreate(ORMModel):
    opportunity_id: UUID
    offer_price: Decimal | None = None
    financing_type: str | None = None
    earnest_money: Decimal | None = None
    requested_closing_date: date | None = None
    buyer_legal_name: str | None = None
    contingencies: list[str] = Field(default_factory=list)
    notes: str | None = None


class TransactionUpdate(ORMModel):
    offer_price: Decimal | None = None
    financing_type: str | None = None
    earnest_money: Decimal | None = None
    requested_closing_date: date | None = None
    buyer_legal_name: str | None = None
    contingencies: list[str] | None = None
    notes: str | None = None


class TransactionTransition(ORMModel):
    status: TransactionStatus
    notes: str | None = None


class TransactionRead(ORMModel):
    id: UUID
    public_id: str
    realtor_id: UUID
    opportunity_id: UUID
    listing_id: UUID
    investor_id: UUID
    criteria_id: UUID
    status: str
    offer_price: Decimal | None = None
    financing_type: str | None = None
    earnest_money: Decimal | None = None
    requested_closing_date: date | None = None
    buyer_legal_name: str | None = None
    contingencies: list
    notes: str | None = None
