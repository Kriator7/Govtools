from decimal import Decimal

from app.integrations.email.mock import MockEmailProvider
from app.integrations.telegram.mock import MockTelegramProvider
from app.integrations.twilio.mock import MockSMSProvider
from app.models.enums import OpportunityStatus
from app.models.investor import Investor
from app.models.investor_criteria import InvestorCriteria
from app.models.listing import Listing
from app.models.opportunity import Opportunity
from app.services.communications import CommunicationService
from app.services.telegram.inbound import process_telegram_update
from app.services.telegram.realtor_agent import RealtorTelegramService
from app.utilities.ids import next_public_id


def test_start_command_stores_operator_chat_id(db, realtor, tmp_path):
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "message": {
                "text": "/start",
                "chat": {"id": 4242},
                "from": {"id": 4242},
            }
        },
        telegram=telegram,
    )
    assert result["ok"] is True
    assert result["chat_id"] == "4242"
    assert realtor.telegram_chat_id == "4242"
    assert "Test Operator" in telegram.sent[0]["text"]


def test_telegram_alert_uses_url_and_callback_rows(db, realtor, tmp_path):
    _investor, _listing, opportunity = _opportunity(db, realtor, listing_url="https://example.invalid/listing")
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    comms = CommunicationService(db, telegram=telegram, sms=MockSMSProvider(tmp_path / "sms.json"), email=MockEmailProvider(tmp_path / "email.json"))
    RealtorTelegramService(db, comms=comms).alert_opportunity(realtor, opportunity)
    buttons = telegram.sent[0]["buttons"]
    assert buttons[0][0]["url"] == "https://example.invalid/listing"
    assert buttons[1][0]["callback_data"].startswith("approve:")


def test_approve_callback_notifies(db, realtor, tmp_path):
    _investor, _listing, opportunity = _opportunity(db, realtor)
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "callback_query": {
                "id": "cb-1",
                "data": f"approve:{opportunity.public_id}",
                "message": {"chat": {"id": 4242}},
            }
        },
        telegram=telegram,
    )
    assert result["ok"] is True
    assert result["action"] == "approve"
    db.refresh(opportunity)
    assert opportunity.status == OpportunityStatus.INVESTOR_NOTIFIED.value
    assert any("Approved" in item["text"] for item in telegram.sent)


def _opportunity(db, realtor, listing_url: str | None = None):
    investor = Investor(
        public_id=next_public_id(db, "INV"),
        realtor_id=realtor.id,
        name="Test Contact",
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
        mls_listing_id="TG1",
        street_address="1 Test",
        city="Las Vegas",
        state="NV",
        zip_code="89123",
        asking_price=Decimal("360000"),
        arv=Decimal("400000"),
        property_type="single_family",
        bedrooms=3,
        bathrooms=2,
        sqft=1600,
        listing_url=listing_url,
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
    return investor, listing, opportunity
