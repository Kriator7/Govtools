from wellness_agent.menu import handle_menu_callback
from wellness_agent.snapshot import load_current_inbox
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []
        self.callbacks = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup, "parse_mode": parse_mode})
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
    from wellness_agent.clients import save_client_phone

    save_client_phone("88", "7025550100", source="typed", user_id="88")
    tg = _FakeTelegram()
    pick = handle_telegram_update(_tap("w:tile:klow"), tg)
    assert pick["action"] == "tile"
    assert pick["product"] == "klow"
    photos = [item for item in tg.sent if "photo" in item]
    assert len(photos) == 1
    assert photos[0]["photo"].endswith("klow.jpg")
    qty = handle_menu_callback(_tap("w:qty:klow")["callback_query"], tg)
    assert qty["action"] == "qty"
    qty_photos = [item for item in tg.sent if str(item.get("photo") or "").endswith("service.jpg")]
    assert qty_photos
    assert "dry vials" in (qty_photos[0].get("caption") or "").lower()
    ask = handle_menu_callback(_tap("w:ask:klow:2")["callback_query"], tg)
    assert ask == {"ok": True, "action": "ask", "chat_id": "88", "product": "klow", "qty": "2"}
    ask_buttons = [
        btn["text"]
        for item in tg.sent
        for row in (item.get("reply_markup") or {}).get("inline_keyboard") or []
        for btn in row
    ]
    assert "Yes — Las Vegas resident" in ask_buttons
    assert "Not in Las Vegas" in ask_buttons
    confirm = handle_telegram_update(_tap("w:yes:klow:2", callback_id="cb2"), tg)
    assert confirm["action"] == "order-confirm"
    assert confirm["product"] == "klow"
    inbox = load_current_inbox()
    assert inbox.orders.new is True
    assert "klow" in inbox.orders.detail.lower()
    assert "7025550100" in inbox.orders.detail.replace("-", "") or "+17025550100" in inbox.orders.detail
    assert inbox.payments.new is False
    texts = [item.get("text") or item.get("caption") or "" for item in tg.sent]
    assert any("Got it. The TrueHold team will call" in text for text in texts)
    assert any("required documentation" in text for text in texts)
    assert any("Las Vegas" in text for text in texts)
    assert any("dry" in text.lower() for text in texts)
    assert not any("waiver" in text.lower() for text in texts)
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
    assert labels == ["Order this", "See info sheet", "See menu"]
