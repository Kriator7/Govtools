from wellness_agent.identity import REQUIRED_USERNAME, WrongTelegramBotError, assert_wellness_telegram_username
from wellness_agent.telegram_inbound import HELP, handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []

    def send_message(self, chat_id, text):
        self.sent.append({"chat_id": chat_id, "text": text})
        return {"ok": True}

    def send_document(self, chat_id, path, caption=""):
        self.sent.append({"chat_id": chat_id, "document": str(path), "caption": caption})
        return {"ok": True}


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


def test_telegram_start_and_inbox_and_order():
    tg = _FakeTelegram()
    start = handle_telegram_update(
        {"message": {"text": "/start", "chat": {"id": 99}}},
        tg,
    )
    assert start["action"] == "help"
    inbox = handle_telegram_update(
        {"message": {"text": "/inbox", "chat": {"id": 99}}},
        tg,
    )
    assert inbox["action"] == "inbox"
    assert any("TrueHold Wellness — business inbox" in item["text"] for item in tg.sent)
    assert any("Orders:" in item["text"] for item in tg.sent)
    order = handle_telegram_update(
        {"message": {"text": "/order 2x starter kit", "chat": {"id": 99}}},
        tg,
    )
    assert order["action"] == "order"
    assert any("Interest order recorded" in item["text"] for item in tg.sent)
    assert any("TrueHold Wellness alert — order" in item["text"] for item in tg.sent)
