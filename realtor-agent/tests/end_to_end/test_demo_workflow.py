from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.opportunity import Opportunity
from app.models.transaction import Transaction
from app.services.demo import run_demo


def test_first_milestone_workflow(db):
    result = run_demo(db)
    assert result["ok"] is True
    assert result["transaction_id"].startswith("TX-")
    assert result["document_status"] == "DRAFT"
    assert db.query(Opportunity).count() >= 1
    assert db.query(Transaction).count() == 1
    assert db.query(Document).count() == 1
    events = [row.event for row in db.query(AuditLog).all()]
    assert "INVESTORS_IMPORTED" in events
    assert "LISTING_INGESTED" in events
    assert "MATCH_DETECTED" in events
    assert "APPROVE_INVESTOR_NOTIFICATION" in events
    assert "TRANSACTION_CREATED" in events
    assert "DOCUMENT_GENERATED" in events
    assert any("Telegram alert" in item["message"] for item in result["timeline"])
