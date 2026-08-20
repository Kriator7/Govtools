import json

import pytest

from mr_north.identity import WrongTelegramBotError, assert_north_telegram_username
from mr_north.telegram import NorthTelegram, split_telegram_text


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_identity_rejects_wellness_and_realtor():
    with pytest.raises(WrongTelegramBotError, match="THWellness_bot"):
        assert_north_telegram_username("THWellness_bot")
    with pytest.raises(WrongTelegramBotError, match="PirateEye_bot"):
        assert_north_telegram_username("@PirateEye_bot")


def test_identity_accepts_north_bot():
    assert assert_north_telegram_username("CryptoNorthBot") == "CryptoNorthBot"


def test_identity_locks_expected_username(monkeypatch):
    monkeypatch.setenv("NORTH_TELEGRAM_USERNAME", "CryptoNorthBot")
    with pytest.raises(WrongTelegramBotError, match="CryptoNorthBot"):
        assert_north_telegram_username("SomeOtherBot")


def test_split_telegram_text_respects_limit():
    chunks = split_telegram_text("a" * 5000, limit=4096)
    assert all(len(chunk) <= 4096 for chunk in chunks)
    assert "".join(chunks) == "a" * 5000


def test_send_report_posts_sendMessage():
    calls = []

    def opener(request, timeout=15):
        body = json.loads(request.data.decode("utf-8")) if request.data else {}
        calls.append({"url": request.full_url, "body": body})
        if request.full_url.endswith("/getMe"):
            return _FakeResponse({"ok": True, "result": {"username": "CryptoNorthBot"}})
        return _FakeResponse({"ok": True, "result": {"message_id": 11}})

    client = NorthTelegram("123:abc", opener=opener)
    assert client.assert_identity() == "CryptoNorthBot"
    ids = client.send_report("99", "Mr North hourly — Bureau of Labor Statistics")
    assert ids == ["11"]
    send = calls[-1]
    assert send["url"].endswith("/sendMessage")
    assert send["body"]["chat_id"] == "99"
    assert "Bureau of Labor Statistics" in send["body"]["text"]
    assert "123:abc" in send["url"]


def test_assert_identity_refuses_wellness_token():
    def opener(request, timeout=15):
        return _FakeResponse({"ok": True, "result": {"username": "THWellness_bot"}})

    client = NorthTelegram("wellness-token", opener=opener)
    with pytest.raises(WrongTelegramBotError, match="THWellness_bot"):
        client.assert_identity()
