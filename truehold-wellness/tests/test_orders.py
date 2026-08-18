from pathlib import Path

from thw.config import get_settings
from thw.email_inbox import parse_order_email
from thw.models import WellnessOrder
from thw.orders import ingest_inbox, notify_order
from thw.telegram_mock import MockWellnessTelegram


def test_parse_order_email_fields():
    parsed = parse_order_email(
        {
            "from": "buyer@example.invalid",
            "subject": "Order: 2x Wellness starter kit",
            "body": "Customer: Test Buyer\nProduct: Wellness starter kit\nQuantity: 2",
            "id": "m1",
        }
    )
    assert parsed["customer_name"] == "Test Buyer"
    assert parsed["product"] == "Wellness starter kit"
    assert parsed["quantity"] == 2


def test_ingest_and_notify_writes_npeppers_outbox(db, tmp_path):
    inbox = Path(__file__).resolve().parents[1] / "data" / "imports" / "sample_order_emails.json"
    created = ingest_inbox(db, inbox)
    assert len(created) >= 1
    telegram = MockWellnessTelegram(outbox_path=tmp_path / "tg.json")
    notify_order(db, created[0], telegram=telegram)
    assert telegram.sent
    assert "TrueHold Wellness order" in telegram.sent[0]["text"]
    assert "@Npeppers_bot" in telegram.sent[0]["text"]
    assert "PirateEye" in telegram.sent[0]["text"]
    assert db.query(WellnessOrder).count() >= 1
    get_settings.cache_clear()


def test_duplicate_source_message_is_skipped(db):
    inbox = Path(__file__).resolve().parents[1] / "data" / "imports" / "sample_order_emails.json"
    first = ingest_inbox(db, inbox)
    second = ingest_inbox(db, inbox)
    assert first
    assert second == []
