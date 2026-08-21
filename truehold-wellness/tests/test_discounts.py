from wellness_agent.clients import save_client_phone
from wellness_agent.discounts import (
    COLLEGE_CODE,
    extract_code,
    is_code_only_message,
    staff_discount_line,
    strip_code,
)
from wellness_agent.knowledge.talk import reply
from wellness_agent.session_store import discount_code
from wellness_agent.snapshot import load_current_inbox
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup, "parse_mode": parse_mode})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append({"caption": caption, "text": caption, "photo": str(path), "message_effect_id": message_effect_id})
        return {"ok": True}

    def send_document(self, chat_id, path, caption="", reply_markup=None, filename=None, parse_mode=None, message_effect_id=None):
        self.sent.append({"caption": caption, "document": str(path)})
        return {"ok": True}

    def answer_callback_query(self, callback_id, text=None, show_alert=False):
        return {"ok": True}


def _msg(text: str, chat_id: int = 99):
    return {"message": {"text": text, "chat": {"id": chat_id, "type": "private"}, "from": {"id": chat_id}}}


def test_extract_college_code():
    assert extract_code("adpilv2026") == COLLEGE_CODE
    assert extract_code("code ADPILV2026 please") == COLLEGE_CODE
    assert strip_code("/order 2x klow ADPILV2026") == "/order 2x klow"
    assert extract_code("no code here") is None
    assert is_code_only_message("ADPILV2026")
    assert is_code_only_message("code ADPILV2026 please")
    assert not is_code_only_message("/order 2x klow ADPILV2026")


def test_college_discount_question_uses_approved_copy():
    spoken = reply("Do college students get a discount?", chat_id="student-chat")
    assert spoken.source == "seed-discount"
    assert "ADPILV2026" in spoken.text
    assert "10%" in spoken.text
    assert "realtor" not in spoken.text.lower()


def test_sending_code_saves_it_on_the_chat():
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("ADPILV2026"), tg)
    assert result["action"] == "discount-code"
    assert discount_code("99") == COLLEGE_CODE
    blob = "\n".join(str(item.get("text") or item.get("caption") or "") for item in tg.sent)
    assert COLLEGE_CODE in blob
    assert "10%" in blob


def test_order_with_code_notifies_staff_to_apply_ten_percent():
    save_client_phone("99", "7025550100", source="test", user_id="99")
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("/order 2x klow ADPILV2026"), tg)
    assert result["action"] == "order-confirm"
    inbox = load_current_inbox()
    assert COLLEGE_CODE in inbox.orders.detail
    assert "10%" in inbox.orders.detail
    assert staff_discount_line(COLLEGE_CODE) in inbox.orders.detail
    blob = "\n".join(str(item.get("caption") or item.get("text") or "") for item in tg.sent)
    assert COLLEGE_CODE in blob
