from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.enums import RejectionReason
from app.schemas.common import ORMModel


class OpportunityRead(ORMModel):
    id: UUID
    public_id: str
    realtor_id: UUID
    listing_id: UUID
    investor_id: UUID
    criteria_id: UUID
    transaction_id: UUID | None = None
    score: Decimal
    score_category: str
    explanation: dict
    status: str
    match_version: int
    rejection_reason: str | None = None
    rejection_notes: str | None = None
    snooze_until: datetime | None = None


class OpportunityDecision(ORMModel):
    notes: str | None = None


class OpportunityReject(ORMModel):
    reason: RejectionReason
    notes: str | None = None


class OpportunitySnooze(ORMModel):
    hours: int = Field(default=24, ge=1, le=720)
    notes: str | None = None
