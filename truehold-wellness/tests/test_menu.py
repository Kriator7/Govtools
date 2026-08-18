from wellness_agent.menu import handle_menu_callback
from wellness_agent.snapshot import load_current_inbox
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []
        self.callbacks = []

    def send_message(self, chat_id, text, reply_markup=None):
        self.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        return {"ok": True}

    def send_document(self, chat_id, path, caption=""):
        self.sent.append({"chat_id": chat_id, "document": str(path), "caption": caption})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None):
        self.sent.append(
            {
                "chat_id": chat_id,
                "photo": str(path),
                "caption": caption,
                "reply_markup": reply_markup,
            }
        )
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        self.callbacks.append(callback_query_id)
        return {"ok": True}


def _tap(data, chat_id=88, user_id=88, callback_id="cb1"):
    return {
        "callback_query": {
            "id": callback_id,
            "data": data,
            "from": {"id": user_id},
            "message": {"chat": {"id": chat_id, "type": "private"}},
        }
    }


def test_picture_menu_order_flow_notifies_without_staff_leak():
    tg = _FakeTelegram()
    pick = handle_telegram_update(_tap("w:pick:klow"), tg)
    assert pick["action"] == "pick"
    assert pick["product"] == "klow"
    qty = handle_menu_callback(_tap("w:qty:klow")["callback_query"], tg)
    assert qty["action"] == "qty"
    ask = handle_menu_callback(_tap("w:ask:klow:2")["callback_query"], tg)
    assert ask == {"ok": True, "action": "ask", "chat_id": "88", "product": "klow", "qty": "2"}
    confirm = handle_telegram_update(_tap("w:yes:klow:2", callback_id="cb2"), tg)
    assert confirm["action"] == "order-confirm"
    assert confirm["product"] == "klow"
    inbox = load_current_inbox()
    assert inbox.orders.new is True
    assert "klow" in inbox.orders.detail.lower()
    assert inbox.payments.new is False
    texts = [item.get("text") or "" for item in tg.sent]
    assert any("Got it. The TrueHold team will confirm" in text for text in texts)
    assert not any("TrueHold Wellness alert — order" in text for text in texts)
    assert any(str(item.get("document", "")).endswith("klow.pdf") for item in tg.sent)
    assert "cb2" in tg.callbacks


def test_info_sheet_from_picture_keeps_two_choices():
    tg = _FakeTelegram()
    result = handle_telegram_update(_tap("w:info:semax"), tg)
    assert result["action"] == "info"
    assert any(str(item.get("document", "")).endswith("semax.pdf") for item in tg.sent)
    buttons = [item.get("reply_markup") for item in tg.sent if item.get("reply_markup")]
    assert buttons
    labels = [btn["text"] for row in buttons[-1]["inline_keyboard"] for btn in row]
    assert labels == ["Order this", "See info sheet", "See all photos"]
