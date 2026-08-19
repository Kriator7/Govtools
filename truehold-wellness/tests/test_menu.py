from wellness_agent.menu import (
    BUY_BACK,
    BUY_MENU,
    BUY_NOT_LV,
    BUY_ORDER,
    BUY_PREP,
    BUY_QTY_1,
    BUY_SHIP,
    handle_menu_callback,
)
from wellness_agent.snapshot import load_current_inbox
from wellness_agent.team import button_label, current_host
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []
        self.callbacks = []
        self.deleted = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup, "parse_mode": parse_mode})
        return {"ok": True}

    def send_document(self, chat_id, path, caption="", reply_markup=None, filename=None, parse_mode=None, message_effect_id=None):
        self.sent.append(
            {
                "chat_id": chat_id,
                "document": str(path),
                "caption": caption,
                "reply_markup": reply_markup,
                "filename": filename,
                "parse_mode": parse_mode,
                "message_effect_id": message_effect_id,
            }
        )
        return {"ok": True, "provider_message_id": str(len(self.sent))}

    def delete_message(self, chat_id, message_id):
        self.deleted.append((str(chat_id), str(message_id)))
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append(
            {
                "chat_id": chat_id,
                "photo": str(path),
                "caption": caption,
                "reply_markup": reply_markup,
                "parse_mode": parse_mode,
                "message_effect_id": message_effect_id,
            }
        )
        return {"ok": True}

    def edit_message_caption(self, chat_id, message_id, caption, reply_markup=None, parse_mode=None):
        self.sent.append(
            {
                "chat_id": chat_id,
                "message_id": str(message_id),
                "caption": caption,
                "text": caption,
                "reply_markup": reply_markup,
                "parse_mode": parse_mode,
                "edited": True,
            }
        )
        return {"ok": True}

    def edit_message_reply_markup(self, chat_id, message_id, reply_markup=None):
        self.sent.append(
            {
                "chat_id": chat_id,
                "message_id": str(message_id),
                "reply_markup": reply_markup,
                "cleared": not (reply_markup or {}).get("inline_keyboard"),
            }
        )
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        self.callbacks.append(callback_query_id)
        return {"ok": True}


def _tap(data, chat_id=88, user_id=88, callback_id="cb1", message_id=10):
    return {
        "callback_query": {
            "id": callback_id,
            "data": data,
            "from": {"id": user_id},
            "message": {"chat": {"id": chat_id, "type": "private"}, "message_id": message_id},
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
    qty_step = [item for item in tg.sent if item.get("edited") or "How many vials" in str(item.get("caption") or "")]
    assert qty_step
    assert "1 of 2" in (qty_step[-1].get("caption") or "")
    assert "dry vials" in (qty_step[-1].get("caption") or "").lower()
    qty_rows = qty_step[-1]["reply_markup"]["inline_keyboard"]
    assert qty_rows[0] == [{"text": BUY_QTY_1, "callback_data": "w:ask:klow:1", "style": "success"}]
    assert all(len(row) == 1 for row in qty_rows)
    ask = handle_menu_callback(_tap("w:ask:klow:2")["callback_query"], tg)
    assert ask == {"ok": True, "action": "ask", "chat_id": "88", "product": "klow", "qty": "2"}
    ask_buttons = [
        btn["text"]
        for item in tg.sent
        for row in (item.get("reply_markup") or {}).get("inline_keyboard") or []
        for btn in row
    ]
    assert BUY_PREP in ask_buttons
    assert BUY_SHIP in ask_buttons
    assert BUY_NOT_LV in ask_buttons
    confirm = handle_telegram_update(_tap("w:go:klow:2:prep", callback_id="cb2"), tg)
    assert confirm["action"] == "order-confirm"
    assert confirm["product"] == "klow"
    inbox = load_current_inbox()
    assert inbox.orders.new is True
    assert "klow" in inbox.orders.detail.lower()
    assert "7025550100" in inbox.orders.detail.replace("-", "") or "+17025550100" in inbox.orders.detail
    assert inbox.payments.new is False
    assert "Inventory:" in inbox.orders.detail
    texts = [item.get("text") or item.get("caption") or "" for item in tg.sent]
    assert any("You're in" in text for text in texts)
    assert any("required documentation" in text for text in texts)
    assert any("Las Vegas" in text for text in texts)
    assert any("not back at the start" in text.lower() for text in texts)
    assert any("dry" in text.lower() for text in texts)
    assert not any("waiver" in text.lower() for text in texts)
    assert not any("TrueHold Wellness alert — order" in text for text in texts)
    assert not any("document" in item for item in tg.sent)
    done_markups = [item.get("reply_markup") for item in tg.sent if "You're in" in str(item.get("caption") or item.get("text") or "")]
    done_labels = [
        btn["text"]
        for markup in done_markups
        for row in (markup or {}).get("inline_keyboard") or []
        for btn in row
    ]
    assert BUY_ORDER not in done_labels
    assert any("Team" in label for label in done_labels)
    assert any("Sheet" in str(item.get("reply_markup") or "") for item in tg.sent)
    assert "cb2" in tg.callbacks


def test_info_sheet_sends_telegram_pdf_not_website_link():
    tg = _FakeTelegram()
    result = handle_telegram_update(_tap("w:info:semax"), tg)
    assert result["action"] == "info"
    docs = [item for item in tg.sent if "document" in item]
    assert docs
    caption = docs[0]["caption"]
    assert "locked information sheet" in caption.lower()
    assert "Telegram file" in caption
    assert "Zelle" in caption
    assert "trueholdwellness.com" not in caption
    assert "http" not in caption.lower()
    labels = [btn["text"] for row in docs[0]["reply_markup"]["inline_keyboard"] for btn in row]
    host = current_host("88")
    assert BUY_ORDER in labels
    assert button_label(host, "prep") in labels
    assert "⬅️ Menu" in labels
    assert "⬅️ Back" in labels
    assert button_label(host, "team") in labels
    assert "url" not in str(docs[0]["reply_markup"])
    assert docs[0]["filename"] == "TrueHold Wellness locked information sheet — Semax.pdf"
    assert docs[0]["document"].endswith(docs[0]["filename"])
    assert docs[0]["parse_mode"] == "HTML"
    assert "<b>" in caption


def test_nad_info_sheet_is_telegram_file_not_shop_page():
    tg = _FakeTelegram()
    result = handle_telegram_update(_tap("w:info:nad"), tg)
    assert result["action"] == "info"
    docs = [item for item in tg.sent if "document" in item]
    assert docs
    assert docs[0]["filename"] == "TrueHold Wellness locked information sheet — NAD+.pdf"
    assert docs[0]["document"].endswith(docs[0]["filename"])
    assert "1000 mg" in docs[0]["caption"]
    assert "trueholdwellness.com" not in docs[0]["caption"]
    assert "http" not in docs[0]["caption"].lower()
    assert "url" not in str(docs[0]["reply_markup"])


def test_second_sheet_send_replaces_prior_copy():
    tg = _FakeTelegram()
    handle_telegram_update(_tap("w:info:semax", callback_id="s1"), tg)
    handle_telegram_update(_tap("w:info:semax", callback_id="s2"), tg)
    docs = [item for item in tg.sent if "document" in item]
    assert len(docs) == 2
    assert all(
        item["filename"] == "TrueHold Wellness locked information sheet — Semax.pdf" for item in docs
    )
    assert tg.deleted == [("88", "1")]


def test_interest_order_decrements_on_hand_when_set():
    from wellness_agent.clients import save_client_phone
    from wellness_agent.stock import load_stock, set_on_hand

    save_client_phone("88", "7025550100", source="typed", user_id="88")
    set_on_hand("klow", 10)
    tg = _FakeTelegram()
    confirm = handle_telegram_update(_tap("w:yes:klow:2", callback_id="cb2"), tg)
    assert confirm["action"] == "order-confirm"
    state = load_stock()
    assert state["products"]["klow"]["on_hand"] == 8
    inbox = load_current_inbox()
    assert "10 → 8 on hand" in inbox.orders.detail


def test_interest_order_logs_adjustment_when_on_hand_unset():
    from wellness_agent.clients import save_client_phone
    from wellness_agent.stock import load_stock

    save_client_phone("88", "7025550100", source="typed", user_id="88")
    tg = _FakeTelegram()
    confirm = handle_telegram_update(_tap("w:yes:klow:1", callback_id="cb3"), tg)
    assert confirm["action"] == "order-confirm"
    state = load_stock()
    assert state["products"]["klow"]["on_hand"] is None
    assert state["adjustments"][-1]["delta"] == -1
    inbox = load_current_inbox()
    assert "on-hand not set yet" in inbox.orders.detail


def test_order_without_phone_does_not_touch_inventory():
    from wellness_agent.stock import load_stock, set_on_hand

    set_on_hand("klow", 5)
    tg = _FakeTelegram()
    result = handle_telegram_update(_tap("w:yes:klow:2"), tg)
    assert result["action"] == "need-phone"
    assert load_stock()["products"]["klow"]["on_hand"] == 5
    assert any("Share my phone" in str(item.get("reply_markup") or "") for item in tg.sent)


def test_slash_order_matching_sku_uses_same_inventory_path():
    from wellness_agent.clients import save_client_phone
    from wellness_agent.stock import load_stock, set_on_hand

    save_client_phone("99", "7025550199", source="typed", user_id="99")
    set_on_hand("semax", 4)
    tg = _FakeTelegram()
    result = handle_telegram_update(
        {
            "message": {
                "text": "/order 2x semax",
                "chat": {"id": 99, "type": "private"},
                "from": {"id": 99},
            }
        },
        tg,
    )
    assert result["action"] == "order-confirm"
    assert result["product"] == "semax"
    assert load_stock()["products"]["semax"]["on_hand"] == 2


def test_prep_card_is_policy_only_not_dosing():
    tg = _FakeTelegram()
    result = handle_telegram_update(_tap("w:prep:semax"), tg)
    assert result["action"] == "prep"
    photos = [item for item in tg.sent if "photo" in item]
    assert photos
    caption = photos[-1]["caption"]
    assert "Prep" in caption
    assert "Las Vegas" in caption
    assert "dry" in caption.lower()
    assert "units" not in caption.lower()
    assert "reconstitut" not in caption.lower()
    assert photos[-1]["parse_mode"] == "HTML"
    labels = [btn["text"] for row in photos[-1]["reply_markup"]["inline_keyboard"] for btn in row]
    host = current_host("88")
    assert button_label(host, "sheet") in labels
    assert BUY_ORDER in labels
    assert "url" not in str(photos[-1]["reply_markup"])


def test_order_confirm_plays_celebrate_effect():
    from wellness_agent.clients import save_client_phone
    from wellness_agent.telegram_copy import CELEBRATE_EFFECT_ID

    save_client_phone("88", "7025550100", source="typed", user_id="88")
    tg = _FakeTelegram()
    confirm = handle_telegram_update(_tap("w:yes:semax:1", callback_id="cb9"), tg)
    assert confirm["action"] == "order-confirm"
    photos = [item for item in tg.sent if "photo" in item]
    assert any(item.get("message_effect_id") == CELEBRATE_EFFECT_ID for item in photos)
    assert any("You're in" in (item.get("caption") or "") for item in photos)
    assert "cb9" in tg.callbacks


def test_quick_menu_uses_emoji_name_grid():
    tg = _FakeTelegram()
    handle_telegram_update(_tap("w:menu"), tg)
    menus = [item for item in tg.sent if (item.get("reply_markup") or {}).get("inline_keyboard")]
    labels = [btn["text"] for row in menus[-1]["reply_markup"]["inline_keyboard"] for btn in row]
    assert "🧠 Semax" in labels
    assert "⚡ NAD+" in labels
    host = current_host("88")
    assert button_label(host, "prep") in labels
    assert button_label(host, "team") in labels
    assert menus[-1]["parse_mode"] == "HTML"


def _labels(item: dict) -> list[str]:
    return [
        btn["text"]
        for row in (item.get("reply_markup") or {}).get("inline_keyboard") or []
        for btn in row
    ]


def test_team_card_has_back_and_menu_distinct_from_copy_email():
    tg = _FakeTelegram()
    handle_menu_callback(_tap("w:tile:nad")["callback_query"], tg)
    team = handle_menu_callback(_tap("w:team:nad")["callback_query"], tg)
    assert team["action"] == "schedule"
    photos = [item for item in tg.sent if "photo" in item]
    labels = _labels(photos[-1])
    data = [
        btn.get("callback_data")
        for row in photos[-1]["reply_markup"]["inline_keyboard"]
        for btn in row
    ]
    assert "📧 Copy email" in labels
    assert "💳 Debit" in labels
    assert BUY_BACK in labels
    assert BUY_MENU in labels
    assert "🕊️ Menu" not in labels
    assert "🕊️ Email" not in labels
    assert "w:back" in data
    assert "w:menu" in data
    back = handle_menu_callback(_tap("w:back", callback_id="back1")["callback_query"], tg)
    assert back == {"ok": True, "action": "tile", "chat_id": "88", "product": "nad"}
    after = [item for item in tg.sent if "photo" in item][-1]
    assert "nad" in str(after.get("photo") or "").lower()
    assert BUY_ORDER in _labels(after)


def test_team_from_menu_back_returns_to_menu():
    tg = _FakeTelegram()
    handle_menu_callback(_tap("w:menu")["callback_query"], tg)
    handle_menu_callback(_tap("w:team")["callback_query"], tg)
    back = handle_menu_callback(_tap("w:back", callback_id="back2")["callback_query"], tg)
    assert back["action"] == "menu"
    labels = _labels(tg.sent[-1])
    assert "🧠 Semax" in labels


def test_team_from_not_lv_back_returns_to_fulfillment():
    tg = _FakeTelegram()
    handle_menu_callback(_tap("w:qty:nad")["callback_query"], tg)
    handle_menu_callback(_tap("w:ask:nad:1")["callback_query"], tg)
    handle_menu_callback(_tap("w:team:nad:1")["callback_query"], tg)
    back = handle_menu_callback(_tap("w:back", callback_id="back3")["callback_query"], tg)
    assert back == {"ok": True, "action": "ask", "chat_id": "88", "product": "nad", "qty": "1"}
    cards = [item for item in tg.sent if "2 of 2" in str(item.get("caption") or "")]
    assert cards
    labels = _labels(cards[-1])
    assert BUY_PREP in labels
    assert BUY_BACK in labels
    assert BUY_MENU in labels


def test_team_menu_opens_quick_menu():
    tg = _FakeTelegram()
    handle_menu_callback(_tap("w:team:nad")["callback_query"], tg)
    result = handle_menu_callback(_tap("w:menu", callback_id="menu2")["callback_query"], tg)
    assert result["action"] == "menu"
    labels = _labels(tg.sent[-1])
    assert "🧠 Semax" in labels
