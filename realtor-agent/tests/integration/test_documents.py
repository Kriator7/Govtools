from datetime import date
from decimal import Decimal

from app.models.enums import DocumentStatus
from app.models.investor import Investor
from app.models.investor_criteria import InvestorCriteria
from app.models.listing import Listing
from app.models.opportunity import Opportunity
from app.services.documents.engine import DocumentEngine, DocumentValidationError
from app.services.transactions.engine import TransactionService
from app.utilities.ids import next_public_id
import pytest


def _transaction(db, realtor):
    investor = Investor(public_id=next_public_id(db, "INV"), realtor_id=realtor.id, name="ABC Capital LLC")
    db.add(investor)
    db.flush()
    criteria = InvestorCriteria(
        public_id=next_public_id(db, "CRT"),
        realtor_id=realtor.id,
        investor_id=investor.id,
        name="Test",
    )
    listing = Listing(
        public_id=next_public_id(db, "LST"),
        realtor_id=realtor.id,
        mls_listing_id="NV12345",
        street_address="123 Main Street",
        city="Las Vegas",
        state="NV",
        zip_code="89123",
        asking_price=Decimal("425000"),
        property_type="single_family",
    )
    db.add_all([criteria, listing])
    db.flush()
    opportunity = Opportunity(
        public_id=next_public_id(db, "OPP"),
        realtor_id=realtor.id,
        listing_id=listing.id,
        investor_id=investor.id,
        criteria_id=criteria.id,
        score=94,
        score_category="excellent",
        explanation={},
    )
    db.add(opportunity)
    db.flush()
    return TransactionService(db).create_from_opportunity(realtor, opportunity)


def test_missing_fields_block_generation(db, realtor):
    transaction = _transaction(db, realtor)
    engine = DocumentEngine(db)
    with pytest.raises(DocumentValidationError) as exc:
        engine.generate(realtor, transaction)
    assert "earnest_money" in exc.value.missing
    assert "financing_type" in exc.value.missing


def test_generate_draft_requires_review(db, realtor):
    transaction = _transaction(db, realtor)
    transaction.buyer_legal_name = "ABC Capital LLC"
    transaction.offer_price = Decimal("425000")
    transaction.earnest_money = Decimal("5000")
    transaction.financing_type = "cash"
    transaction.requested_closing_date = date(2026, 9, 30)
    document = DocumentEngine(db).generate(realtor, transaction)
    assert document.status == DocumentStatus.DRAFT.value
    assert document.review_required is True
    assert "realtor review" in (document.notes or "").lower()
    assert document.generated_path
