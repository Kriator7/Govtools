from wellness_agent.clients import save_client_phone
from wellness_agent.menu import (
    BUY_DONE_TEAM,
    BUY_ORDER,
    BUY_PICKUP,
    BUY_PREP,
    BUY_QTY_1,
    BUY_SHIP,
    after_pick_keyboard,
    done_keyboard,
    fulfill_keyboard,
    handle_menu_callback,
    qty_keyboard,
)
from wellness_agent.snapshot import load_current_inbox
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []
        self.callbacks = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.sent.append({"text": text, "reply_markup": reply_markup, "caption": text})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append(
            {
                "photo": str(path),
                "caption": caption,
                "reply_markup": reply_markup,
                "message_effect_id": message_effect_id,
            }
        )
        return {"ok": True}

    def edit_message_caption(self, chat_id, message_id, caption, reply_markup=None, parse_mode=None):
        self.sent.append(
            {
                "edited": True,
                "message_id": str(message_id),
                "caption": caption,
                "reply_markup": reply_markup,
            }
        )
        return {"ok": True}

    def edit_message_reply_markup(self, chat_id, message_id, reply_markup=None):
        self.sent.append({"cleared": True, "message_id": str(message_id), "reply_markup": reply_markup})
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        self.callbacks.append(callback_query_id)
        return {"ok": True}


def _tap(data, callback_id="c1", message_id=22):
    return {
        "id": callback_id,
        "data": data,
        "from": {"id": 88},
        "message": {"chat": {"id": 88, "type": "private"}, "message_id": message_id},
    }


def _first_button(markup: dict) -> dict:
    return markup["inline_keyboard"][0][0]


def test_buy_keyboards_stack_primary_cta_in_the_same_slot():
    qty = qty_keyboard("nad")
    fulfill = fulfill_keyboard("nad", "1")
    done = done_keyboard("nad")
    tile = after_pick_keyboard("nad")
    assert _first_button(tile)["text"] == BUY_ORDER
    assert _first_button(tile)["style"] == "success"
    assert _first_button(qty)["text"] == BUY_QTY_1
    assert _first_button(qty)["style"] == "success"
    assert _first_button(fulfill)["text"] == BUY_PREP
    assert _first_button(fulfill)["style"] == "success"
    assert _first_button(done)["text"] == BUY_DONE_TEAM
    assert _first_button(done)["style"] == "success"
    assert BUY_ORDER not in [btn["text"] for row in done["inline_keyboard"] for btn in row]
    assert all(len(row) == 1 for row in qty["inline_keyboard"])
    assert {btn["text"] for row in fulfill["inline_keyboard"] for btn in row} >= {
        BUY_PREP,
        BUY_SHIP,
        BUY_PICKUP,
    }


def test_qty_and_fulfill_edit_the_same_product_card():
    tg = _FakeTelegram()
    qty = handle_menu_callback(_tap("w:qty:nad"), tg)
    assert qty["action"] == "qty"
    edited = [item for item in tg.sent if item.get("edited")]
    assert edited
    assert edited[-1]["message_id"] == "22"
    assert "1 of 2" in edited[-1]["caption"]
    assert "Las Vegas · we call" not in edited[-1]["caption"]
    ask = handle_menu_callback(_tap("w:ask:nad:1"), tg)
    assert ask["action"] == "ask"
    assert "2 of 2" in [item["caption"] for item in tg.sent if item.get("edited")][-1]
    rows = [item["reply_markup"]["inline_keyboard"] for item in tg.sent if item.get("edited")][-1]
    assert rows[0][0]["text"] == BUY_PREP


def test_expired_callback_toast_still_opens_menu():
    class _BoomTelegram(_FakeTelegram):
        def answer_callback_query(self, callback_query_id, text=None):
            raise RuntimeError("query is too old")

    tg = _BoomTelegram()
    result = handle_menu_callback(_tap("w:menu"), tg)
    assert result["action"] == "menu"
    assert any(item.get("reply_markup") for item in tg.sent)


def test_ship_choice_lands_on_done_not_order_again():
    save_client_phone("88", "7025550100", source="test", user_id="88")
    tg = _FakeTelegram()
    result = handle_telegram_update(
        {"callback_query": _tap("w:go:nad:1:ship", callback_id="ship1")},
        tg,
    )
    assert result["action"] == "order-confirm"
    assert result["fulfillment"] == "ship"
    inbox = load_current_inbox()
    assert "Ship dry vials" in inbox.orders.detail
    photos = [item for item in tg.sent if "You're in" in str(item.get("caption") or "")]
    assert photos
    labels = [btn["text"] for row in photos[-1]["reply_markup"]["inline_keyboard"] for btn in row]
    assert labels[0] == BUY_DONE_TEAM
    assert BUY_ORDER not in labels
    assert any(item.get("cleared") for item in tg.sent)
