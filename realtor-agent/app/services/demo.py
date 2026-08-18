"""Local demonstration using the Numbers workbook as a test template."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.audit_log import AuditLog
from app.models.enums import FinancingType, InvestorResponse, OpportunityStatus, TransactionStatus
from app.models.opportunity import Opportunity
from app.services.documents.engine import DocumentEngine
from app.services.matching.runner import OpportunityMatcher
from app.services.mls.ingest import ListingIngestService
from app.services.providers import get_mls_provider
from app.services.seed import seed_pirates_ig, seed_realtor
from app.services.sms.investor_notify import InvestorNotificationService
from app.services.telegram.realtor_agent import RealtorTelegramService
from app.services.transactions.engine import TransactionService


def run_demo(db: Session) -> dict:
    realtor = seed_realtor(db)
    investor = seed_pirates_ig(db, realtor)
    ingested = ListingIngestService(db, get_mls_provider()).sync(realtor, incremental=False)
    created = OpportunityMatcher(db).match_all(realtor)
    telegram = RealtorTelegramService(db)
    for opportunity in created:
        telegram.alert_opportunity(realtor, opportunity)

    ready = [item for item in created if item.status != OpportunityStatus.AWAITING_ARV.value]
    if not ready:
        return {
            "ok": False,
            "error": "No fully screened opportunities (ARV may still be required)",
            "ingested": ingested,
        }

    opportunity = ready[0]
    telegram.approve(realtor, opportunity, "Approved during local demo")
    notify = InvestorNotificationService(db)
    notify.notify_approved(realtor, opportunity)
    transaction = notify.record_response(realtor, opportunity, InvestorResponse.YES, "YES")
    assert transaction is not None
    transaction.buyer_legal_name = "Pirates IG LLC (test template)"
    transaction.offer_price = Decimal("360000")
    transaction.earnest_money = Decimal("5000")
    transaction.financing_type = FinancingType.CASH.value
    transaction.requested_closing_date = date(2026, 9, 30)
    TransactionService(db).transition(
        realtor, transaction, TransactionStatus.PROPERTY_REVIEW, "Demo advances to property review"
    )
    TransactionService(db).transition(
        realtor, transaction, TransactionStatus.OFFER_PREPARATION, "Demo advances to offer prep"
    )
    document = DocumentEngine(db).generate(realtor, transaction, "purchase_agreement")

    timeline = (
        db.query(ActivityLog)
        .filter(ActivityLog.realtor_id == realtor.id)
        .order_by(ActivityLog.occurred_at.asc())
        .all()
    )
    audits = db.query(AuditLog).order_by(AuditLog.occurred_at.asc()).all()
    return {
        "ok": True,
        "realtor_id": realtor.public_id,
        "investor_id": investor.public_id,
        "ingested": ingested,
        "opportunities": [item.public_id for item in created],
        "approved_opportunity": opportunity.public_id,
        "transaction_id": transaction.public_id,
        "document_id": document.public_id,
        "document_status": document.status,
        "document_path": document.generated_path,
        "review_notice": document.notes,
        "timeline": [{"at": row.occurred_at.isoformat(), "event": row.event_type, "message": row.message} for row in timeline],
        "audit_events": [row.event for row in audits],
    }
