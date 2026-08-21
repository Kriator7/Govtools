from fastapi import APIRouter
from sqlalchemy import func

from app.dependencies import ActiveRealtor, DbSession
from app.models.analytics_event import AnalyticsEvent
from app.models.opportunity import Opportunity
from app.models.transaction import Transaction

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def analytics_summary(db: DbSession, realtor: ActiveRealtor) -> dict:
    """Operational counters for a later dashboard. Phase 10 will expand this."""
    events = (
        db.query(AnalyticsEvent.event_name, func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.realtor_id == realtor.id)
        .group_by(AnalyticsEvent.event_name)
        .all()
    )
    opportunities = db.query(Opportunity).filter(Opportunity.realtor_id == realtor.id).count()
    approved = (
        db.query(Opportunity)
        .filter(Opportunity.realtor_id == realtor.id, Opportunity.status.like("APPROVED%"))
        .count()
    )
    rejected = (
        db.query(Opportunity)
        .filter(Opportunity.realtor_id == realtor.id, Opportunity.status == "REJECTED")
        .count()
    )
    closed = (
        db.query(Transaction)
        .filter(Transaction.realtor_id == realtor.id, Transaction.status == "CLOSED")
        .count()
    )
    return {
        "events": {name: count for name, count in events},
        "opportunities": opportunities,
        "approvals": approved,
        "rejections": rejected,
        "closed_transactions": closed,
    }
