from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.dependencies import ActiveRealtor, DbSession
from app.models.enums import RejectionReason
from app.models.opportunity import Opportunity
from app.schemas.opportunity import (
    OpportunityDecision,
    OpportunityRead,
    OpportunityReject,
    OpportunitySnooze,
)
from app.services.matching.runner import OpportunityMatcher
from app.services.sms.investor_notify import InvestorNotificationService
from app.services.telegram.realtor_agent import RealtorTelegramService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=list[OpportunityRead])
def list_opportunities(db: DbSession, realtor: ActiveRealtor) -> list[Opportunity]:
    return db.query(Opportunity).filter(Opportunity.realtor_id == realtor.id).all()


@router.post("/match")
def run_matching(db: DbSession, realtor: ActiveRealtor) -> dict:
    created = OpportunityMatcher(db).match_all(realtor)
    telegram = RealtorTelegramService(db)
    for opportunity in created:
        telegram.alert_opportunity(realtor, opportunity)
    db.commit()
    return {"created": len(created), "ids": [item.public_id for item in created]}


@router.get("/{opportunity_id}", response_model=OpportunityRead)
def get_opportunity(opportunity_id: UUID, db: DbSession, realtor: ActiveRealtor) -> Opportunity:
    return _get(db, realtor, opportunity_id)


@router.get("/{opportunity_id}/details")
def opportunity_details(opportunity_id: UUID, db: DbSession, realtor: ActiveRealtor) -> dict:
    opportunity = _get(db, realtor, opportunity_id)
    return RealtorTelegramService(db).details(opportunity)


@router.post("/{opportunity_id}/approve", response_model=OpportunityRead)
def approve_opportunity(
    opportunity_id: UUID,
    payload: OpportunityDecision,
    db: DbSession,
    realtor: ActiveRealtor,
) -> Opportunity:
    opportunity = _get(db, realtor, opportunity_id)
    service = RealtorTelegramService(db)
    service.approve(realtor, opportunity, payload.notes)
    InvestorNotificationService(db).notify_approved(realtor, opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.post("/{opportunity_id}/reject", response_model=OpportunityRead)
def reject_opportunity(
    opportunity_id: UUID,
    payload: OpportunityReject,
    db: DbSession,
    realtor: ActiveRealtor,
) -> Opportunity:
    opportunity = _get(db, realtor, opportunity_id)
    RealtorTelegramService(db).reject(realtor, opportunity, payload.reason, payload.notes)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.post("/{opportunity_id}/snooze", response_model=OpportunityRead)
def snooze_opportunity(
    opportunity_id: UUID,
    payload: OpportunitySnooze,
    db: DbSession,
    realtor: ActiveRealtor,
) -> Opportunity:
    opportunity = _get(db, realtor, opportunity_id)
    RealtorTelegramService(db).snooze(realtor, opportunity, payload.hours, payload.notes)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.post("/{opportunity_id}/investor-response")
def investor_response(opportunity_id: UUID, response: str, db: DbSession, realtor: ActiveRealtor) -> dict:
    from app.models.enums import InvestorResponse

    opportunity = _get(db, realtor, opportunity_id)
    try:
        parsed = InvestorResponse(response.upper())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Response must be YES, NO, or MORE_INFO") from exc
    transaction = InvestorNotificationService(db).record_response(realtor, opportunity, parsed)
    db.commit()
    return {
        "opportunity_id": opportunity.public_id,
        "status": opportunity.status,
        "transaction_id": transaction.public_id if transaction else None,
    }


def _get(db, realtor, opportunity_id: UUID) -> Opportunity:
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.id == opportunity_id, Opportunity.realtor_id == realtor.id)
        .one_or_none()
    )
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity
