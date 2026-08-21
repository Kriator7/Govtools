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


def test_damian_join_links_damian_not_test_operator(db, realtor, tmp_path):
    from app.services.seed import DAMIAN_NAME, upsert_damian_realtor

    damian = upsert_damian_realtor(db, {"name": DAMIAN_NAME})
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "message": {
                "chat": {"id": -5372586958, "title": "MaximumMint & Agent Real", "type": "group"},
                "new_chat_members": [
                    {
                        "id": 7592412078,
                        "is_bot": False,
                        "first_name": "Damian",
                        "username": "damianlasvegas",
                    }
                ],
            }
        },
        telegram=telegram,
    )
    assert result["action"] == "damian_joined"
    assert result["telegram_user_id"] == "7592412078"
    db.refresh(damian)
    db.refresh(realtor)
    assert damian.telegram_user_id == "7592412078"
    assert damian.telegram_chat_id == "-5372586958"
    assert realtor.name == "Test Operator"
    assert realtor.telegram_user_id is None or realtor.telegram_user_id != "7592412078"
    assert "PirateEye is live" in telegram.sent[0]["text"]
    assert "Test Operator" not in telegram.sent[0]["text"]


def test_group_start_from_damian_keeps_test_operator_identity(db, realtor, tmp_path):
    from app.services.seed import DAMIAN_NAME, upsert_damian_realtor

    damian = upsert_damian_realtor(db, {"name": DAMIAN_NAME})
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "message": {
                "text": "/start@PirateEye_bot",
                "chat": {"id": -5372586958, "type": "group"},
                "from": {"id": 7592412078, "username": "damianlasvegas"},
            }
        },
        telegram=telegram,
    )
    assert result["action"] == "linked"
    db.refresh(damian)
    db.refresh(realtor)
    assert realtor.telegram_chat_id == "-5372586958"
    assert realtor.telegram_user_id != "7592412078"
    assert damian.telegram_user_id == "7592412078"
    assert "test flow" in telegram.sent[0]["text"]


def test_link_operator_group_chat_sets_both_realtors(db, realtor, monkeypatch):
    from app.config import get_settings
    from app.services.seed import DAMIAN_NAME, link_operator_group_chat, upsert_damian_realtor

    damian = upsert_damian_realtor(db, {"name": DAMIAN_NAME})
    monkeypatch.setenv("TELEGRAM_OPERATOR_CHAT_ID", "-5372586958")
    get_settings.cache_clear()
    assert link_operator_group_chat(db) == "-5372586958"
    db.refresh(realtor)
    db.refresh(damian)
    assert realtor.telegram_chat_id == "-5372586958"
    assert damian.telegram_chat_id == "-5372586958"
    assert realtor.name == "Test Operator"
    assert damian.name == DAMIAN_NAME


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


def test_hello_from_operator_asks_how_it_can_help(db, realtor, tmp_path):
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "message": {
                "text": "hello",
                "chat": {"id": -5372586958, "type": "group"},
                "from": {"id": 1150046483, "username": "MaximumMint_AMINT"},
            }
        },
        telegram=telegram,
    )
    assert result["action"] == "help"
    assert "How can I help" in telegram.sent[0]["text"]
    assert "@PirateEye_bot" in telegram.sent[0]["text"]
    assert "Agent Real" in telegram.sent[0]["text"]
    assert "Mr_North" not in telegram.sent[0]["text"]
    assert "Wellness" not in telegram.sent[0]["text"]


def test_help_command_and_bot_mention(db, realtor, tmp_path):
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    for text in ("/help", "/help@PirateEye_bot", "@PirateEye_bot", "Agent Real", "hey"):
        telegram.sent.clear()
        result = process_telegram_update(
            db,
            realtor,
            {
                "message": {
                    "text": text,
                    "chat": {"id": -5372586958, "type": "group"},
                    "from": {"id": 1150046483, "username": "MaximumMint_AMINT"},
                }
            },
            telegram=telegram,
        )
        assert result["action"] == "help", text
        assert "How can I help" in telegram.sent[0]["text"]


def test_damian_hello_is_not_a_buy_box_note(db, realtor, tmp_path):
    from app.services.seed import DAMIAN_NAME, upsert_damian_realtor

    upsert_damian_realtor(db, {"name": DAMIAN_NAME})
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "message": {
                "text": "hello",
                "chat": {"id": -5372586958, "type": "group"},
                "from": {"id": 7592412078, "username": "damianlasvegas"},
            }
        },
        telegram=telegram,
    )
    assert result["action"] == "help"
    assert "buy box" not in telegram.sent[0]["text"].lower() or "How can I help" in telegram.sent[0]["text"]
    assert "Saved your note" not in telegram.sent[0]["text"]


def test_unrelated_group_chatter_stays_ignored(db, realtor, tmp_path):
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "message": {
                "text": "see you at lunch",
                "chat": {"id": -5372586958, "type": "group"},
                "from": {"id": 1150046483, "username": "MaximumMint_AMINT"},
            }
        },
        telegram=telegram,
    )
    assert result.get("ignored") is True
    assert telegram.sent == []
