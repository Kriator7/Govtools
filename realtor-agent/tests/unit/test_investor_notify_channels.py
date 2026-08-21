from decimal import Decimal

from app.integrations.email.mock import MockEmailProvider
from app.integrations.twilio.mock import MockSMSProvider
from app.models.enums import OpportunityStatus
from app.models.investor import Investor
from app.models.investor_criteria import InvestorCriteria
from app.models.listing import Listing
from app.models.opportunity import Opportunity
from app.services.communications import CommunicationService
from app.services.sms.investor_notify import InvestorNotificationService
from app.services.telegram.realtor_agent import RealtorTelegramService
from app.utilities.ids import next_public_id


def test_notify_sends_sms_and_email_copy(db, realtor, tmp_path):
    investor = Investor(
        public_id=next_public_id(db, "INV"),
        realtor_id=realtor.id,
        name="Pirates IG LLC",
        phone="+15555550100",
        email="cardanomint@gmail.com",
        preferred_channel="sms",
        communication_permissions={"sms": True, "email": True},
    )
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
        mls_listing_id="N1",
        street_address="123 Main Street",
        city="Las Vegas",
        state="NV",
        zip_code="89123",
        asking_price=Decimal("360000"),
        arv=Decimal("400000"),
        property_type="single_family",
        bedrooms=3,
        bathrooms=2,
        sqft=1600,
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
    sms = MockSMSProvider(outbox_path=tmp_path / "sms.json")
    email = MockEmailProvider(outbox_path=tmp_path / "email.json")
    comms = CommunicationService(db, sms=sms, email=email)
    telegram = RealtorTelegramService(db)
    telegram.approve(realtor, opportunity, "test")
    InvestorNotificationService(db, comms=comms).notify_approved(realtor, opportunity)
    assert opportunity.status == OpportunityStatus.INVESTOR_NOTIFIED.value
    assert sms.sent
    assert "Interested?" in sms.sent[0]["body"]
    assert email.sent
    assert email.sent[0]["to"] == "cardanomint@gmail.com"


def test_notify_holds_when_text_permission_is_no(db, realtor, tmp_path):
    investor = Investor(
        public_id=next_public_id(db, "INV"),
        realtor_id=realtor.id,
        name="Held Investor",
        phone="+15555550199",
        email="held@example.test",
        preferred_channel="sms",
        communication_permissions={"sms": False, "email": False},
    )
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
        mls_listing_id="N2",
        street_address="456 Held Street",
        city="Las Vegas",
        state="NV",
        zip_code="89123",
        asking_price=Decimal("360000"),
        arv=Decimal("400000"),
        property_type="single_family",
        bedrooms=3,
        bathrooms=2,
        sqft=1600,
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
    sms = MockSMSProvider(outbox_path=tmp_path / "sms.json")
    email = MockEmailProvider(outbox_path=tmp_path / "email.json")
    comms = CommunicationService(db, sms=sms, email=email)
    telegram = RealtorTelegramService(db)
    telegram.approve(realtor, opportunity, "test")
    InvestorNotificationService(db, comms=comms).notify_approved(realtor, opportunity)
    assert sms.sent == []
    assert opportunity.status == OpportunityStatus.APPROVED_FOR_INVESTOR_NOTIFICATION.value
