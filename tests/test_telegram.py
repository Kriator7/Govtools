import json
import urllib.error

import pytest

from mr_north.identity import WrongTelegramBotError, assert_north_telegram_username
from mr_north.telegram import (
    DEFAULT_GROUP_CHAT_ID,
    NorthTelegram,
    TelegramError,
    configured_chat_ids,
    split_telegram_text,
)


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
    assert assert_north_telegram_username("Mr_North_bot") == "Mr_North_bot"
    assert assert_north_telegram_username("@Mr_North_bot") == "Mr_North_bot"


def test_identity_rejects_other_bot():
    with pytest.raises(WrongTelegramBotError, match="Mr_North_bot"):
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
            return _FakeResponse({"ok": True, "result": {"username": "Mr_North_bot"}})
        return _FakeResponse({"ok": True, "result": {"message_id": 11}})

    client = NorthTelegram("123:abc", opener=opener)
    assert client.assert_identity() == "Mr_North_bot"
    ids = client.send_report("99", "Mr North hourly — Bureau of Labor Statistics")
    assert ids == ["11"]
    send = calls[-1]
    assert send["url"].endswith("/sendMessage")
    assert send["body"]["chat_id"] == "99"
    assert "Bureau of Labor Statistics" in send["body"]["text"]
    assert "123:abc" in send["url"]


def test_getupdates_conflict_explains_chat_id():
    def opener(request, timeout=15):
        raise urllib.error.HTTPError(
            request.full_url,
            409,
            "Conflict",
            hdrs=None,
            fp=None,
        )

    client = NorthTelegram("123:abc", opener=opener)
    with pytest.raises(TelegramError, match="NORTH_TELEGRAM_CHAT_ID"):
        client.capture_chat_id()


def test_assert_identity_refuses_wellness_token():
    def opener(request, timeout=15):
        return _FakeResponse({"ok": True, "result": {"username": "THWellness_bot"}})

    client = NorthTelegram("wellness-token", opener=opener)
    with pytest.raises(WrongTelegramBotError, match="THWellness_bot"):
        client.assert_identity()


def test_configured_chat_ids_combines_both_locations(monkeypatch):
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_ID", "111")
    monkeypatch.setenv("NORTH_TELEGRAM_GROUP_CHAT_ID", DEFAULT_GROUP_CHAT_ID)
    monkeypatch.delenv("NORTH_TELEGRAM_CHAT_IDS", raising=False)
    monkeypatch.delenv("NORTH_TELEGRAM_CHAT_PATH", raising=False)
    assert configured_chat_ids() == ["111", DEFAULT_GROUP_CHAT_ID]


def test_configured_chat_ids_skips_pirateeye_group(monkeypatch):
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_ID", "-5372586958,222")
    monkeypatch.setenv("NORTH_TELEGRAM_GROUP_CHAT_ID", DEFAULT_GROUP_CHAT_ID)
    assert configured_chat_ids() == ["222", DEFAULT_GROUP_CHAT_ID]


def test_configured_chat_ids_accepts_comma_list(monkeypatch):
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_ID", "111,-1003939359929")
    monkeypatch.setenv("NORTH_TELEGRAM_GROUP_CHAT_ID", "")
    assert configured_chat_ids() == ["111", "-1003939359929"]
