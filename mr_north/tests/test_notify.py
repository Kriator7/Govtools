import json

import pytest

from mr_north.compose import compose_alert
from mr_north.models import AlertTrigger
from mr_north.notify import NotifyError, alert_payload, send_alert
from mr_north.telegram import TelegramError


class _FakeResponse:
    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b"ok"


def _btc_alert():
    return compose_alert(
        AlertTrigger(
            type="btc_threshold",
            headline="BTC threshold",
            detail="BTC crossed the $65K watch level.",
        )
    )


def test_payload_always_includes_catalyst_and_text():
    payload = alert_payload(_btc_alert())
    assert payload["source"] == "mr-north"
    assert payload["agent"] == "mr-north"
    assert payload["trigger"]["type"] == "btc_threshold"
    assert payload["catalyst"]["kind"] == "geopolitical_market_catalyst"
    assert "Strait of Hormuz" in payload["catalyst"]["summary"]
    assert "Strait of Hormuz" in payload["text"]
    assert "TrueHold Wellness" not in payload["text"]
    assert "business" not in payload["catalyst"]
    json.dumps(payload)


def test_dry_run_does_not_call_webhook():
    called = {"count": 0}

    def opener(_request, timeout=15):
        called["count"] += 1
        return _FakeResponse()

    result = send_alert(
        _btc_alert(),
        webhook_url="https://example.test/alerts",
        dry_run=True,
        opener=opener,
    )
    assert result.dry_run is True
    assert result.delivered is False
    assert called["count"] == 0
    assert result.payload["catalyst"]["title"] == "Alert — geopolitical / market catalyst"


def test_send_posts_json_including_catalyst(monkeypatch):
    monkeypatch.delenv("NORTH_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("NORTH_TELEGRAM_CHAT_ID", raising=False)
    captured = {}

    def opener(request, timeout=15):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["content_type"] = request.headers["Content-type"]
        captured["user_agent"] = request.headers["User-agent"]
        return _FakeResponse()

    result = send_alert(
        _btc_alert(),
        webhook_url="https://example.test/alerts",
        opener=opener,
    )
    assert result.delivered is True
    assert captured["url"] == "https://example.test/alerts"
    assert captured["content_type"].startswith("application/json")
    assert captured["user_agent"] == "mr-north/0.1"
    body = json.loads(captured["body"].decode("utf-8"))
    assert body["catalyst"]["kind"] == "geopolitical_market_catalyst"
    assert body["agent"] == "mr-north"
    assert "Macro Liquidity" in body["text"]


def test_send_uses_env_webhook(monkeypatch):
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://example.test/from-env")
    monkeypatch.delenv("NORTH_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("NORTH_TELEGRAM_CHAT_ID", raising=False)

    def opener(request, timeout=15):
        assert request.full_url == "https://example.test/from-env"
        return _FakeResponse()

    result = send_alert(_btc_alert(), opener=opener)
    assert result.destination == "https://example.test/from-env"


def test_send_without_destination_raises(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("NORTH_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("NORTH_TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(NotifyError, match="NORTH_TELEGRAM_BOT_TOKEN"):
        send_alert(_btc_alert(), webhook_url=None)


def test_send_ignores_wellness_telegram_token(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("NORTH_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("NORTH_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "wellness-token-must-not-be-used")
    with pytest.raises(NotifyError, match="NORTH_TELEGRAM_BOT_TOKEN"):
        send_alert(_btc_alert(), webhook_url=None)


def test_send_drops_report_on_north_telegram(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("NORTH_TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_ID", "42")
    captured = {}

    class _FakeNorth:
        def assert_identity(self):
            return "Mr_North_bot"

        def send_report(self, chat_id, text):
            captured["chat_id"] = chat_id
            captured["text"] = text
            return ["1"]

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    result = send_alert(_btc_alert())
    assert result.delivered is True
    assert result.destination == "telegram:@Mr_North_bot:42"
    assert captured["chat_id"] == "42"
    assert "Strait of Hormuz" in captured["text"]
    assert "TrueHold Wellness" not in captured["text"]


def test_send_fans_out_to_both_north_chats(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("NORTH_TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_ID", "111")
    monkeypatch.setenv("NORTH_TELEGRAM_GROUP_CHAT_ID", "-1003939359929")
    captured = {"chats": []}

    class _FakeNorth:
        def assert_identity(self):
            return "Mr_North_bot"

        def send_report(self, chat_id, text):
            captured["chats"].append(chat_id)
            captured["text"] = text
            return ["1"]

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    result = send_alert(_btc_alert())
    assert result.delivered is True
    assert result.destination == "telegram:@Mr_North_bot:111,-1003939359929"
    assert captured["chats"] == ["111", "-1003939359929"]
    assert "Strait of Hormuz" in captured["text"]


def test_send_skips_pirateeye_group(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("NORTH_TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_ID", "-5372586958")
    monkeypatch.setenv("NORTH_TELEGRAM_GROUP_CHAT_ID", "-1003939359929")
    captured = {"chats": []}

    class _FakeNorth:
        def assert_identity(self):
            return "Mr_North_bot"

        def send_report(self, chat_id, text):
            captured["chats"].append(chat_id)
            return ["1"]

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    result = send_alert(_btc_alert())
    assert captured["chats"] == ["-1003939359929"]
    assert "-5372586958" not in (result.destination or "")


def test_send_fails_if_maximummint_north_group_is_missed(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("NORTH_TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_ID", "1150046483")
    monkeypatch.setenv("NORTH_TELEGRAM_GROUP_CHAT_ID", "-1003939359929")

    class _FakeNorth:
        def assert_identity(self):
            return "Mr_North_bot"

        def send_report(self, chat_id, text):
            if chat_id == "-1003939359929":
                raise TelegramError("bot is not a member")
            return ["1"]

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    with pytest.raises(NotifyError, match="MaximumMint & North"):
        send_alert(_btc_alert())


def test_send_retries_discovered_maximummint_north_group(tmp_path, monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("NORTH_TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_ID", "1150046483")
    monkeypatch.setenv("NORTH_TELEGRAM_GROUP_CHAT_ID", "-1003939359929")
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_PATH", str(tmp_path / "telegram_chat.json"))
    captured = {"chats": []}

    class _FakeNorth:
        def assert_identity(self):
            return "Mr_North_bot"

        def send_report(self, chat_id, text):
            if chat_id == "-1003939359929":
                raise TelegramError("chat not found")
            captured["chats"].append(chat_id)
            return ["1"]

        def discover_north_group(self, timeout=0):
            return "-5777888999"

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    result = send_alert(_btc_alert())
    assert result.delivered is True
    assert captured["chats"] == ["1150046483", "-5777888999"]
    assert "telegram:@Mr_North_bot:1150046483,-5777888999" == result.destination


def test_send_does_not_post_to_wrong_titled_group(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("NORTH_TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_ID", "1150046483")
    monkeypatch.setenv("NORTH_TELEGRAM_GROUP_CHAT_ID", "-1003939359929")
    captured = {"chats": []}

    class _FakeNorth:
        def assert_identity(self):
            return "Mr_North_bot"

        def resolve_group_chat_id(self, configured=""):
            return ""

        def group_id_is_wrong_title(self, chat_id):
            return chat_id == "-1003939359929"

        def discover_north_group(self, timeout=0):
            return ""

        def send_report(self, chat_id, text):
            captured["chats"].append(chat_id)
            return ["1"]

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    with pytest.raises(NotifyError, match="MaximumMint & North"):
        send_alert(_btc_alert())
    assert captured["chats"] == ["1150046483"]
    assert "-1003939359929" not in captured["chats"]
