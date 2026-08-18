from pathlib import Path

from wellness_agent.cli import main
from wellness_agent.email_reflex import classify_email, ingest_reflex_emails
from wellness_agent.operator_store import load_operator_chats
from wellness_agent.snapshot import load_current_inbox
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []

    def send_message(self, chat_id, text, reply_markup=None):
        self.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        return {"ok": True}

    def send_document(self, chat_id, path, caption=""):
        self.sent.append({"chat_id": chat_id, "document": str(path), "caption": caption})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None):
        self.sent.append({"chat_id": chat_id, "photo": str(path), "caption": caption})
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        return {"ok": True}


def test_start_does_not_link_customer_as_operator():
    tg = _FakeTelegram()
    handle_telegram_update({"message": {"text": "/start", "chat": {"id": 501}, "from": {"id": 501}}}, tg)
    assert load_operator_chats() == []
    assert any("say hi" in (item.get("text") or "").lower() for item in tg.sent)


def test_order_marks_orders_new_and_keeps_other_categories():
    tg = _FakeTelegram()
    result = handle_telegram_update(
        {"message": {"text": "/order 2x klow", "chat": {"id": 502}, "from": {"id": 502}}},
        tg,
    )
    assert result["action"] == "order"
    assert result["product"] == "klow"
    inbox = load_current_inbox()
    assert inbox.orders.new is True
    assert "klow" in inbox.orders.detail.lower()
    assert inbox.payments.new is False
    assert inbox.shipping.new is False
    assert any("Got it. The TrueHold team will confirm" in item.get("text", "") for item in tg.sent)
    assert not any("TrueHold Wellness alert — order" in item.get("text", "") for item in tg.sent)
    assert any(str(item.get("document", "")).endswith("klow.pdf") for item in tg.sent)


def test_classify_all_original_email_reflexes():
    assert classify_email({"subject": "Order: 2x KLOW", "body": "Quantity: 2"}) == "order"
    assert classify_email({"subject": "Payment received", "body": "Invoice paid"}) == "payment"
    assert classify_email({"subject": "Fulfillment request", "body": "Ready to ship pick list"}) == "fulfillment"
    assert classify_email({"subject": "Shipping issue USPS", "body": "tracking delay"}) == "shipping"
    assert classify_email({"subject": "Cancellation/refund", "body": "please refund"}) == "cancellation"
    assert classify_email({"subject": "Peptide message: Semax", "body": ""}) == "peptide"
    assert classify_email({"subject": "Need a consult", "body": "call back"}) == "business"


def test_ingest_reflex_emails_fires_each_category_once(tmp_path):
    inbox = Path(__file__).resolve().parents[1] / "data" / "imports" / "sample_reflex_emails.json"
    first = ingest_reflex_emails(inbox)
    triggers = [item["trigger"] for item in first]
    assert "order" in triggers
    assert "payment" in triggers
    assert "fulfillment" in triggers
    assert "shipping" in triggers
    assert "cancellation" in triggers
    assert "peptide" in triggers
    assert "business" in triggers
    second = ingest_reflex_emails(inbox)
    assert second == []


def test_ingest_email_cli(capsys):
    assert main(["ingest-email"]) == 0
    out = capsys.readouterr().out
    assert "order" in out
    assert "payment" in out
