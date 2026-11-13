from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from wellness_agent.cli import main
from wellness_agent.clients import save_client_phone
from wellness_agent.delivery import (
    FREE_DELIVERY_THRESHOLD,
    INVOICE_SMALL_PRINT,
    LOCAL_DELIVERY_FEE,
    STAFF_DELIVERY_LINE,
    TELEGRAM_SMALL_PRINT,
    customer_delivery_note,
    delivery_charge,
    format_usd,
    qualifies_for_free_delivery,
)
from wellness_agent.invoice import format_invoice_html, format_invoice_text, quote_invoice
from wellness_agent.knowledge import retrieve, seed_approved_knowledge
from wellness_agent.knowledge.talk import reply
from wellness_agent.menu import ask_step_caption, qty_step_caption
from wellness_agent.snapshot import load_current_inbox
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.sent.append({"text": text, "caption": text, "reply_markup": reply_markup})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append({"caption": caption, "reply_markup": reply_markup})
        return {"ok": True}

    def send_document(self, chat_id, path, caption="", reply_markup=None, filename=None, parse_mode=None, message_effect_id=None):
        self.sent.append({"caption": caption})
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        return {"ok": True}

    def edit_message_caption(self, chat_id, message_id, caption, reply_markup=None, parse_mode=None):
        self.sent.append({"edited": True, "caption": caption, "reply_markup": reply_markup})
        return {"ok": True}

    def edit_message_reply_markup(self, chat_id, message_id, reply_markup=None):
        self.sent.append({"cleared": True})
        return {"ok": True}


def _tap(data, callback_id="c1", message_id=22, chat_id=88):
    return {
        "id": callback_id,
        "data": data,
        "from": {"id": chat_id},
        "message": {"chat": {"id": chat_id, "type": "private"}, "message_id": message_id},
    }


def test_local_delivery_is_twenty_until_two_fifty():
    assert LOCAL_DELIVERY_FEE == Decimal("20.00")
    assert FREE_DELIVERY_THRESHOLD == Decimal("250.00")
    assert delivery_charge(merchandise_subtotal="249.99", fulfillment="delivery") == Decimal("20.00")
    assert delivery_charge(merchandise_subtotal="250", fulfillment="prep") == Decimal("0.00")
    assert delivery_charge(merchandise_subtotal="250.00", fulfillment="delivery") == Decimal("0.00")
    assert delivery_charge(merchandise_subtotal="400", fulfillment="delivery") == Decimal("0.00")
    assert not qualifies_for_free_delivery("249.99")
    assert qualifies_for_free_delivery("250")


def test_pickup_and_ship_do_not_use_the_local_fee():
    assert delivery_charge(merchandise_subtotal="80", fulfillment="pickup") == Decimal("0.00")
    assert delivery_charge(merchandise_subtotal="80", fulfillment="ship") == Decimal("0.00")
    assert customer_delivery_note("ship") == ""
    assert "Pickup" in customer_delivery_note("pickup")
    assert "two vials" in customer_delivery_note("prep")


def test_invoice_charges_twenty_under_threshold():
    when = datetime(2026, 11, 13, 9, 30, tzinfo=ZoneInfo("America/Los_Angeles"))
    quote = quote_invoice(
        merchandise_subtotal="180.00",
        fulfillment="delivery",
        invoice_id="THW-INV-TEST-180",
        detail="1 × KLOW 80 mg (price confirmed on call)",
        when=when,
    )
    text = format_invoice_text(quote)
    html = format_invoice_html(quote)
    assert quote.merchandise_subtotal == "$180.00"
    assert quote.delivery_fee == "$20.00"
    assert quote.total == "$200.00"
    assert quote.delivery_waived is False
    assert INVOICE_SMALL_PRINT in text
    assert "two vials usually does it" in text
    assert "Small print, big save" in html
    assert 'class="small-print"' in html
    assert "font-size: 11px" in html
    assert "$20.00" in html
    assert "THW-INV-TEST-180" in html
    assert "1 × KLOW 80 mg" in html


def test_invoice_waives_delivery_at_two_fifty():
    quote = quote_invoice(merchandise_subtotal="250", fulfillment="delivery", invoice_id="THW-INV-TEST-250")
    text = format_invoice_text(quote)
    html = format_invoice_html(quote)
    assert quote.delivery_fee == "$0.00"
    assert quote.total == "$250.00"
    assert quote.delivery_waived is True
    assert "FREE" in text
    assert "You saved $20.00" in html
    assert INVOICE_SMALL_PRINT in text
    assert format_usd("250") == "$250.00"


def test_invoice_cli_prints_small_print(tmp_path, capsys):
    out = tmp_path / "one-vial.html"
    assert (
        main(
            [
                "invoice",
                "--subtotal",
                "180",
                "--fulfillment",
                "delivery",
                "--invoice-id",
                "THW-INV-CLI-180",
                "--html",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    html = out.read_text(encoding="utf-8")
    assert "THW-INV-CLI-180" in html
    assert "two vials usually does it" in html
    assert main(["invoice", "--subtotal", "250", "--fulfillment", "prep"]) == 0
    printed = capsys.readouterr().out
    assert "Total due: $250.00" in printed
    assert "Local delivery: $0.00" in printed
    assert "two vials usually does it" in printed


def test_qty_caption_nudges_two_vials_in_small_print():
    from wellness_agent.catalog import find_product

    product = find_product("klow")
    qty = qty_step_caption(product)
    ask = ask_step_caption(product, "1")
    assert TELEGRAM_SMALL_PRINT in qty
    assert TELEGRAM_SMALL_PRINT in ask
    assert "two vials usually does it" in qty
    assert len(qty) <= 1024
    assert len(ask) <= 1024


def test_delivery_question_uses_approved_copy():
    spoken = reply("Is delivery free if I spend over $250?", chat_id="fee-chat")
    assert spoken.source == "seed-delivery"
    assert "$20" in spoken.text
    assert "$250" in spoken.text
    assert "two vials" in spoken.text.lower() or "250" in spoken.text


def test_seed_retrieve_ranks_delivery_policy():
    seed_approved_knowledge()
    hits = retrieve("local delivery fee $20")
    assert hits
    assert hits[0]["id"] == "policy-delivery"
    assert "$20" in hits[0]["text"]
    assert "$250" in hits[0]["text"]


def test_prep_order_shows_small_print_and_staff_rule():
    save_client_phone("88", "7025550100", source="test", user_id="88")
    tg = _FakeTelegram()
    result = handle_telegram_update(
        {"callback_query": _tap("w:go:klow:1:prep", callback_id="prep1")},
        tg,
    )
    assert result["action"] == "order-confirm"
    blob = "\n".join(str(item.get("caption") or "") for item in tg.sent)
    assert "two vials usually does it" in blob
    inbox = load_current_inbox()
    assert STAFF_DELIVERY_LINE in inbox.orders.detail
    assert "$20.00" in inbox.orders.detail
    assert "$250.00" in inbox.orders.detail
