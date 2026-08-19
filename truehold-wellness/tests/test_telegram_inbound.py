from wellness_agent.access import STAFF_DENIED
from wellness_agent.identity import REQUIRED_USERNAME, WrongTelegramBotError, assert_wellness_telegram_username
from wellness_agent.operator_store import load_operator_chats, load_operator_user_ids
from wellness_agent.telegram_inbound import HELP, handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []
        self.callbacks = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.sent.append(
            {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": reply_markup,
                "parse_mode": parse_mode,
            }
        )
        return {"ok": True}

    def send_document(self, chat_id, path, caption="", reply_markup=None, filename=None):
        self.sent.append(
            {
                "chat_id": chat_id,
                "document": str(path),
                "caption": caption,
                "reply_markup": reply_markup,
                "filename": filename,
            }
        )
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append(
            {
                "chat_id": chat_id,
                "photo": str(path),
                "caption": caption,
                "reply_markup": reply_markup,
                "parse_mode": parse_mode,
            }
        )
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        self.callbacks.append({"id": callback_query_id, "text": text})
        return {"ok": True}


def _msg(text, chat_id=99, user_id=None, chat_type="private"):
    return {
        "message": {
            "text": text,
            "chat": {"id": chat_id, "type": chat_type},
            "from": {"id": user_id if user_id is not None else chat_id},
        }
    }


def test_wellness_identity_rejects_pirateeye():
    try:
        assert_wellness_telegram_username("PirateEye_bot")
        raise AssertionError("expected WrongTelegramBotError")
    except WrongTelegramBotError as exc:
        assert "PirateEye_bot" in str(exc)


def test_wellness_identity_accepts_thwellness():
    assert assert_wellness_telegram_username("@THWellness_bot") == REQUIRED_USERNAME


def test_customer_copy_uses_documentation_not_waivers():
    from wellness_agent import catalog, clients, menu
    from wellness_agent.telegram_copy import CUSTOMER_HELP, INTRODUCTION, SCHEDULE

    assert len(INTRODUCTION) <= 1024
    blob = "\n".join(
        [
            INTRODUCTION,
            CUSTOMER_HELP,
            SCHEDULE,
            menu.MENU_INTRO,
            menu.CUSTOMER_CONFIRM.format(detail="1x KLOW"),
            menu.ASK_PHONE,
            menu.PHONE_THANKS.format(phone="+17025550100"),
            menu.NEED_PHONE,
            clients.phone_line_for_staff("missing"),
            catalog.format_catalog(),
            catalog.format_product_caption(catalog.find_product("semax")),
        ]
    ).lower()
    assert "waiver" not in blob
    assert "required documentation" in blob
    assert "dry" in blob
    assert "las vegas" in blob
    assert "zelle" in blob
    assert "debit card" in blob
    assert "how it works" in INTRODUCTION.lower()
    assert "welcome to truehold wellness" in INTRODUCTION.lower()
    assert "ownership" in INTRODUCTION.lower() or "nature" in INTRODUCTION.lower()
    assert "adpilv2026" in blob
    assert "10%" in blob
    assert len(INTRODUCTION) <= 1024


def test_start_plays_welcome_with_logo_and_does_not_grant_staff():
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("/start", chat_id=99), tg)
    assert result["action"] == "intro"
    assert result["staff"] is False
    assert load_operator_chats() == []
    assert load_operator_user_ids() == []
    texts = [item.get("text") or item.get("caption") or "" for item in tg.sent]
    blob = "\n".join(texts).lower()
    assert "welcome to truehold wellness" in blob
    assert "how it works" in blob
    assert "tap a name" in blob
    assert not any("Linked as TrueHold Wellness operator" in text for text in texts)
    photos = [item for item in tg.sent if "photo" in item]
    assert len(photos) == 1
    assert photos[0]["photo"].endswith("logo.jpeg")
    assert not any("Share my phone number" in str(item.get("reply_markup") or "") for item in tg.sent)
    menus = [item for item in tg.sent if (item.get("reply_markup") or {}).get("inline_keyboard")]
    labels = [btn["text"] for row in menus[0]["reply_markup"]["inline_keyboard"] for btn in row]
    assert any("KLOW" in label for label in labels)
    assert any("Tirzepatide" in label for label in labels)


def test_hello_after_start_does_not_repeat_intro():
    tg = _FakeTelegram()
    handle_telegram_update(_msg("/start", chat_id=99), tg)
    tg.sent.clear()
    hello = handle_telegram_update(_msg("hello", chat_id=99), tg)
    assert hello["action"] == "greet-again"
    photos = [item for item in tg.sent if "photo" in item]
    assert photos
    assert "wave" in photos[0]["photo"]
    blob = "\n".join((item.get("text") or item.get("caption") or "") for item in tg.sent).lower()
    assert blob.strip()
    assert "send /menu" not in blob
    assert "<b>" in "\n".join((item.get("text") or item.get("caption") or "") for item in tg.sent)


def test_hello_plays_intro_once_then_does_not_repeat():
    tg = _FakeTelegram()
    hello = handle_telegram_update(_msg("hello", chat_id=99), tg)
    assert hello["action"] == "intro"
    texts = [item.get("text") or item.get("caption") or "" for item in tg.sent]
    blob = "\n".join(texts).lower()
    assert "welcome to truehold wellness" in blob
    assert "las vegas residents only" in blob
    assert "dry (lyophilized) vials only" in blob
    assert "required documentation" in blob
    assert "how it works" in blob
    assert not any("waiver" in text.lower() for text in texts)
    assert not any("Share my phone number" in str(item.get("reply_markup") or "") for item in tg.sent)
    photos = [item for item in tg.sent if "photo" in item]
    assert len(photos) == 1
    assert photos[0]["photo"].endswith("logo.jpeg")
    menus = [item for item in tg.sent if (item.get("reply_markup") or {}).get("inline_keyboard")]
    assert menus
    labels = [btn["text"] for row in menus[0]["reply_markup"]["inline_keyboard"] for btn in row]
    assert any("KLOW" in label for label in labels)
    assert any("Tirzepatide" in label for label in labels)
    tg.sent.clear()
    again = handle_telegram_update(_msg("Hey there!", chat_id=99), tg)
    assert again["action"] == "greet-again"
    assert any("photo" in item for item in tg.sent)
    assert any("wave" in str(item.get("photo") or "") for item in tg.sent)


def test_menu_does_not_ask_for_phone():
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("/menu", chat_id=55), tg)
    assert result["action"] == "menu"
    photos = [item for item in tg.sent if "photo" in item]
    assert photos
    assert photos[0]["photo"].endswith("theo-present.jpg")
    assert not any("Share my phone number" in str(item.get("reply_markup") or "") for item in tg.sent)


def test_good_morning_is_a_salutation_on_first_visit():
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("Good morning", chat_id=44), tg)
    assert result["action"] == "intro"
    photos = [item for item in tg.sent if "photo" in item]
    assert photos
    assert photos[0]["photo"].endswith("logo.jpeg")
    assert not any(str(item.get("photo") or "").endswith("klow.jpg") for item in tg.sent)
    assert any((item.get("reply_markup") or {}).get("inline_keyboard") for item in tg.sent)
    assert not any("Share my phone number" in str(item.get("reply_markup") or "") for item in tg.sent)


def test_unrelated_first_message_plays_welcome():
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("what do you sell", chat_id=44), tg)
    assert result["action"] == "intro"
    captions = [item.get("caption") or "" for item in tg.sent]
    assert any("Welcome to TrueHold Wellness" in text for text in captions)
    assert any("How it works" in text for text in captions)
    photos = [item for item in tg.sent if "photo" in item]
    assert photos
    assert photos[0]["photo"].endswith("logo.jpeg")
    assert not any("Share my phone number" in str(item.get("reply_markup") or "") for item in tg.sent)


def test_schedule_email_opens_client_mail_not_gmail_web():
    from wellness_agent.telegram_copy import MAILTO_URL, SCHEDULE, TEAM_EMAIL

    assert TEAM_EMAIL in SCHEDULE
    assert MAILTO_URL.startswith("mailto:trueholdwellness@gmail.com?")
    assert "subject=" in MAILTO_URL
    assert "mail.google.com" not in SCHEDULE
    assert "t.me" not in MAILTO_URL
    assert "@GMAIL" not in SCHEDULE
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("/schedule", chat_id=44), tg)
    assert result["action"] == "schedule"
    buttons = [
        btn
        for item in tg.sent
        for row in (item.get("reply_markup") or {}).get("inline_keyboard") or []
        for btn in row
    ]
    assert buttons
    assert buttons[0]["text"] == "📧 Copy email"
    assert buttons[0]["copy_text"]["text"] == TEAM_EMAIL
    assert "url" not in buttons[0]
    assert buttons[1]["text"] == "💳 Debit"
    assert buttons[1]["url"] == "https://trueholdwellness.com/shop"
    labels = [btn["text"] for btn in buttons]
    assert "⬅️ Back" in labels
    assert "⬅️ Menu" in labels
    assert "🕊️ Menu" not in labels
    assert "🕊️ Email" not in labels
    texts = [item.get("text") or item.get("caption") or "" for item in tg.sent]
    assert any("Zelle" in text for text in texts)
    assert any(TEAM_EMAIL in text for text in texts)
    assert any("mailto:" in text for text in texts)
    assert any(item.get("parse_mode") == "HTML" for item in tg.sent)


def test_customer_inbox_is_denied():
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("/inbox", chat_id=99), tg)
    assert result["action"] == "staff-denied"
    assert any(STAFF_DENIED in (item.get("text") or "") for item in tg.sent)
    assert not any("Orders:" in (item.get("text") or "") for item in tg.sent)


def test_staff_inbox_allowed(monkeypatch):
    monkeypatch.setenv("WELLNESS_OPERATOR_USER_IDS", "42")
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("/inbox", chat_id=42, user_id=42), tg)
    assert result["action"] == "inbox"
    assert any("TrueHold Wellness — business inbox" in (item.get("text") or "") for item in tg.sent)
    assert any("Orders:" in (item.get("text") or "") for item in tg.sent)


def test_staff_stock_allowed(monkeypatch):
    monkeypatch.setenv("WELLNESS_OPERATOR_USER_IDS", "42")
    from wellness_agent.stock import set_on_hand

    set_on_hand("klow", 10)
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("/stock", chat_id=42, user_id=42), tg)
    assert result["action"] == "stock"
    texts = [item.get("text") or "" for item in tg.sent]
    assert any("on-hand inventory" in text.lower() for text in texts)
    assert any("KLOW" in text for text in texts)
    assert any("10 on hand" in text for text in texts)


def test_staff_claim_from_telegram_never_grants(monkeypatch):
    monkeypatch.setenv("WELLNESS_OPERATOR_CLAIM_TOKEN", "correct-token-value")
    tg = _FakeTelegram()
    claimed = handle_telegram_update(_msg("/staff correct-token-value", chat_id=77, user_id=77), tg)
    assert claimed["action"] == "staff-denied"
    assert load_operator_user_ids() == []
    inbox = handle_telegram_update(_msg("/inbox", chat_id=77, user_id=77), tg)
    assert inbox["action"] == "staff-denied"
    assert not any("Orders:" in (item.get("text") or "") for item in tg.sent)


def test_admin_and_operator_commands_never_grant():
    tg = _FakeTelegram()
    for command in ("/admin", "/operator", "/grant", "/staff", "/stock", "/promo"):
        result = handle_telegram_update(_msg(command, chat_id=88, user_id=88), tg)
        assert result["action"] == "staff-denied"


def test_leftover_operator_file_does_not_unlock_inbox(tmp_path, monkeypatch):
    path = tmp_path / "operator.json"
    path.write_text('{"chat_ids": ["501"], "user_ids": ["501"]}', encoding="utf-8")
    monkeypatch.setenv("WELLNESS_OPERATOR_PATH", str(path))
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("/inbox", chat_id=501, user_id=501), tg)
    assert result["action"] == "staff-denied"


def test_allowlisted_staff_inbox_denied_in_group(monkeypatch):
    monkeypatch.setenv("WELLNESS_OPERATOR_USER_IDS", "42")
    tg = _FakeTelegram()
    result = handle_telegram_update(
        _msg("/inbox", chat_id=-100, user_id=42, chat_type="supergroup"),
        tg,
    )
    assert result["action"] == "staff-denied"
    assert not any("Orders:" in (item.get("text") or "") for item in tg.sent)


def test_customer_order_does_not_leak_inbox_snapshot():
    tg = _FakeTelegram()
    order = handle_telegram_update(_msg("/order 2x starter kit", chat_id=99), tg)
    assert order["action"] == "order"
    texts = [item.get("text") or item.get("caption") or "" for item in tg.sent]
    assert any("You're in" in text for text in texts)
    assert any("required documentation" in text for text in texts)
    assert not any("waiver" in text.lower() for text in texts)
    assert not any("TrueHold Wellness alert — order" in text for text in texts)
    assert not any("Orders:" in text for text in texts)


def test_group_member_cannot_use_chat_allowlist(monkeypatch):
    monkeypatch.setenv("WELLNESS_TELEGRAM_CHAT_ID", "-100")
    tg = _FakeTelegram()
    result = handle_telegram_update(
        _msg("/inbox", chat_id=-100, user_id=555, chat_type="supergroup"),
        tg,
    )
    assert result["action"] == "staff-denied"


def test_phone_prompt_menu_button_leaves_the_wait():
    from wellness_agent.menu import ask_for_phone
    from wellness_agent.session_store import awaiting_phone

    tg = _FakeTelegram()
    ask_for_phone(tg, "88")
    assert awaiting_phone("88") is True
    assert any("⬅️ Menu" in str(item.get("reply_markup") or "") for item in tg.sent)
    result = handle_telegram_update(_msg("⬅️ Menu", chat_id=88), tg)
    assert result["action"] == "menu"
    assert awaiting_phone("88") is False
    labels = [
        btn["text"]
        for item in tg.sent
        for row in (item.get("reply_markup") or {}).get("inline_keyboard") or []
        for btn in row
    ]
    assert "🧠 Semax" in labels
    assert any((item.get("reply_markup") or {}).get("remove_keyboard") for item in tg.sent)
