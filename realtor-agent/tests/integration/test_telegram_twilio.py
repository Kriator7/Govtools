from app.integrations.email.mock import MockEmailProvider
from app.integrations.telegram.mock import MockTelegramProvider
from app.integrations.twilio.mock import MockSMSProvider
from app.models.communication import Communication
from app.services.communications import CommunicationService


def test_telegram_sms_and_email_relay(db, realtor, tmp_path):
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    sms = MockSMSProvider(outbox_path=tmp_path / "sms.json")
    email = MockEmailProvider(outbox_path=tmp_path / "email.json")
    comms = CommunicationService(db, telegram=telegram, sms=sms, email=email)
    comms.send_message(
        realtor=realtor,
        recipient="mock-realtor",
        channel="telegram",
        template="opportunity_alert.txt.j2",
        context={
            "address": "123 Main Street",
            "city": "Las Vegas",
            "state": "NV",
            "price": "$425,000",
            "beds": 4,
            "baths": 3,
            "sqft": "2,150",
            "investor": "ABC Capital",
            "score": "94%",
            "reasons": ["Target ZIP"],
            "issues": [],
            "listing_url": "https://example.invalid",
            "opportunity_id": "OPP-2026-000001",
        },
    )
    comms.send_message(
        realtor=realtor,
        recipient="+15551230001",
        channel="sms",
        template="opportunity.txt.j2",
        context={
            "address": "123 Main Street",
            "city": "Las Vegas",
            "state": "NV",
            "zip_code": "89123",
            "price": "$425,000",
            "beds": 4,
            "baths": 3,
            "sqft": "2,150",
            "profile_name": "Las Vegas acquisition",
        },
    )
    comms.send_message(
        realtor=realtor,
        recipient="investor@example.invalid",
        channel="email",
        template="opportunity.txt.j2",
        context={
            "address": "123 Main Street",
            "city": "Las Vegas",
            "state": "NV",
            "zip_code": "89123",
            "price": "$425,000",
            "beds": 4,
            "baths": 3,
            "sqft": "2,150",
            "profile_name": "Las Vegas acquisition",
        },
    )
    assert db.query(Communication).count() == 3
    assert "NEW INVESTOR MATCH" in telegram.sent[0]["text"]
    assert "Interested?" in sms.sent[0]["body"]
    assert email.sent[0]["from"] == "cardanomint@gmail.com"
    assert email.sent[0]["to"] == "cardanomint@gmail.com"
    assert email.sent[0]["intended_recipient"] == "investor@example.invalid"
