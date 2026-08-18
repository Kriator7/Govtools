from wellness_agent.access import STAFF_DENIED
from wellness_agent.identity import REQUIRED_USERNAME, WrongTelegramBotError, assert_wellness_telegram_username
from wellness_agent.operator_store import load_operator_chats, load_operator_user_ids
from wellness_agent.telegram_inbound import HELP, handle_telegram_update


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


def test_help_names_thwellness_not_npeppers():
    assert "@THWellness_bot" in HELP
    assert "Npeppers" not in HELP
    assert "/inbox" not in HELP


def test_start_asks_to_say_hi_and_does_not_grant_staff():
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("/start", chat_id=99), tg)
    assert result["action"] == "say-hi"
    assert result["staff"] is False
    assert load_operator_chats() == []
    assert load_operator_user_ids() == []
    texts = [item.get("text") or "" for item in tg.sent]
    assert any("Say hi to start" in text for text in texts)
    assert not any("Linked as TrueHold Wellness operator" in text for text in texts)
    assert not any("photo" in item for item in tg.sent)


def test_hello_plays_intro_once_then_does_not_repeat():
    tg = _FakeTelegram()
    handle_telegram_update(_msg("/start", chat_id=99), tg)
    hello = handle_telegram_update(_msg("hello", chat_id=99), tg)
    assert hello["action"] == "intro"
    texts = [item.get("text") or "" for item in tg.sent]
    assert any("welcome to TrueHold Wellness" in text for text in texts)
    assert any("Share my phone number" in str(item.get("reply_markup") or "") for item in tg.sent)
    photos = [item for item in tg.sent if "photo" in item]
    assert photos == []
    menus = [item for item in tg.sent if (item.get("reply_markup") or {}).get("inline_keyboard")]
    assert menus
    labels = [btn["text"] for row in menus[0]["reply_markup"]["inline_keyboard"] for btn in row]
    assert "KLOW" in labels
    assert "Tirzepatide" in labels
    tg.sent.clear()
    again = handle_telegram_update(_msg("Hey there!", chat_id=99), tg)
    assert again["action"] == "greet-again"
    assert not any("photo" in item for item in tg.sent)
    assert any("Hi again" in (item.get("text") or "") for item in tg.sent)


def test_good_morning_is_a_salutation_on_first_visit():
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("Good morning", chat_id=44), tg)
    assert result["action"] == "intro"
    assert not any("photo" in item for item in tg.sent)
    assert any((item.get("reply_markup") or {}).get("inline_keyboard") for item in tg.sent)


def test_unrelated_first_message_asks_for_hi():
    tg = _FakeTelegram()
    result = handle_telegram_update(_msg("what do you sell", chat_id=44), tg)
    assert result["action"] == "say-hi"
    assert any("Say hi to start" in (item.get("text") or "") for item in tg.sent)
    assert not any("photo" in item for item in tg.sent)


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
    for command in ("/admin", "/operator", "/grant", "/staff"):
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
    texts = [item.get("text") or "" for item in tg.sent]
    assert any("Got it. The TrueHold team will call" in text for text in texts)
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
