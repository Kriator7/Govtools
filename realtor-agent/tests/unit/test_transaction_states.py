import pytest

from app.models.enums import TRANSACTION_TRANSITIONS, TransactionStatus
from app.services.transactions.engine import InvalidTransition, TransactionService


def test_allowed_happy_path():
    status = TransactionStatus.INVESTOR_INTERESTED
    status = _one(status, TransactionStatus.PROPERTY_REVIEW)
    status = _one(status, TransactionStatus.OFFER_PREPARATION)
    status = _one(status, TransactionStatus.DOCUMENT_REVIEW)
    status = _one(status, TransactionStatus.AWAITING_SIGNATURE)
    status = _one(status, TransactionStatus.OFFER_SUBMITTED)
    status = _one(status, TransactionStatus.UNDER_CONTRACT)
    status = _one(status, TransactionStatus.DUE_DILIGENCE)
    status = _one(status, TransactionStatus.CLOSING)
    status = _one(status, TransactionStatus.CLOSED)
    assert status is TransactionStatus.CLOSED


def test_cannot_skip_to_closed():
    assert TransactionStatus.CLOSED not in TRANSACTION_TRANSITIONS[TransactionStatus.INVESTOR_INTERESTED]


def test_invalid_transition_raises(db, realtor):
    from app.models.investor import Investor
    from app.models.investor_criteria import InvestorCriteria
    from app.models.listing import Listing
    from app.models.opportunity import Opportunity
    from app.utilities.ids import next_public_id

    investor = Investor(public_id=next_public_id(db, "INV"), realtor_id=realtor.id, name="Test")
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
        mls_listing_id="X1",
        street_address="1 Test",
        city="Las Vegas",
        zip_code="89123",
        asking_price=100000,
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
        score=90,
        score_category="excellent",
        explanation={},
    )
    db.add(opportunity)
    db.flush()
    service = TransactionService(db)
    transaction = service.create_from_opportunity(realtor, opportunity)
    with pytest.raises(InvalidTransition):
        service.transition(realtor, transaction, TransactionStatus.CLOSED)


def _one(current: TransactionStatus, nxt: TransactionStatus) -> TransactionStatus:
    assert nxt in TRANSACTION_TRANSITIONS[current]
    return nxt
