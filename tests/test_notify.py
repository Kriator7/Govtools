import json

import pytest

from truehold.crypto_agent.compose import compose_alert
from truehold.crypto_agent.models import AlertTrigger
from truehold.crypto_agent.notify import NotifyError, alert_payload, send_alert


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
    assert payload["source"] == "truehold-crypto-agent"
    assert payload["trigger"]["type"] == "btc_threshold"
    assert payload["catalyst"]["kind"] == "geopolitical_market_catalyst"
    assert "Strait of Hormuz" in payload["catalyst"]["summary"]
    assert "Strait of Hormuz" in payload["text"]
    assert "TrueHold Wellness" not in payload["text"]
    assert "business" not in payload["catalyst"]
    json.dumps(payload)  # must be serializable


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
    captured = {}

    def opener(request, timeout=15):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["content_type"] = request.headers["Content-type"]
        captured["timeout"] = timeout
        return _FakeResponse()

    result = send_alert(
        _btc_alert(),
        webhook_url="https://example.test/alerts",
        opener=opener,
    )
    assert result.delivered is True
    assert captured["url"] == "https://example.test/alerts"
    assert captured["content_type"].startswith("application/json")
    body = json.loads(captured["body"].decode("utf-8"))
    assert body["catalyst"]["kind"] == "geopolitical_market_catalyst"
    assert "Macro Liquidity" in body["text"]


def test_send_uses_env_webhook(monkeypatch):
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://example.test/from-env")

    def opener(request, timeout=15):
        assert request.full_url == "https://example.test/from-env"
        return _FakeResponse()

    result = send_alert(_btc_alert(), opener=opener)
    assert result.destination == "https://example.test/from-env"


def test_send_without_webhook_raises(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    with pytest.raises(NotifyError, match="ALERT_WEBHOOK_URL"):
        send_alert(_btc_alert(), webhook_url=None)
