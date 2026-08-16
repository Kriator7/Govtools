import json

import pytest

from truehold.wellness_agent.compose import compose_alert
from truehold.wellness_agent.models import REQUIRED_CATEGORIES, AlertTrigger
from truehold.wellness_agent.notify import NotifyError, alert_payload, send_alert
from truehold.wellness_agent.snapshot import parse_inbox


class _FakeResponse:
    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b"ok"


def _order_alert():
    return compose_alert(
        AlertTrigger(
            type="order",
            headline="order",
            detail="New TrueHold Wellness order received.",
        )
    )


def test_payload_always_includes_every_inbox_category():
    payload = alert_payload(_order_alert())
    assert payload["source"] == "truehold-wellness-agent"
    assert payload["agent"] == "truehold-wellness-agent"
    assert payload["trigger"]["type"] == "order"
    inbox = payload["inbox"]
    for name in REQUIRED_CATEGORIES:
        assert name in inbox
        assert isinstance(inbox[name]["new"], bool)
        assert inbox[name]["detail"]
    assert "peptide message" in inbox["peptides"]["detail"]
    assert "cancellation/refund" in inbox["cancellations"]["detail"]
    json.dumps(payload)


def test_parse_inbox_rejects_missing_category():
    inbox = compose_alert(AlertTrigger(type="business", headline="business inbox")).inbox.to_dict()
    del inbox["shipping"]
    with pytest.raises(ValueError, match="missing fields"):
        parse_inbox(inbox)


def test_parse_inbox_rejects_crypto_fields():
    inbox = compose_alert(AlertTrigger(type="business", headline="business inbox")).inbox.to_dict()
    inbox["catalyst"] = "Hormuz"
    with pytest.raises(ValueError, match="crypto/macro"):
        parse_inbox(inbox)


def test_dry_run_does_not_call_webhook():
    called = {"count": 0}

    def opener(_request, timeout=15):
        called["count"] += 1
        return _FakeResponse()

    result = send_alert(
        _order_alert(),
        webhook_url="https://example.test/wellness",
        dry_run=True,
        opener=opener,
    )
    assert result.dry_run is True
    assert result.delivered is False
    assert called["count"] == 0
    assert "orders" in result.payload["inbox"]


def test_send_posts_json_including_inbox():
    captured = {}

    def opener(request, timeout=15):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["user_agent"] = request.headers["User-agent"]
        return _FakeResponse()

    result = send_alert(
        _order_alert(),
        webhook_url="https://example.test/wellness",
        opener=opener,
    )
    assert result.delivered is True
    assert captured["url"] == "https://example.test/wellness"
    assert captured["user_agent"] == "truehold-wellness-agent/0.1"
    body = json.loads(captured["body"].decode("utf-8"))
    assert body["agent"] == "truehold-wellness-agent"
    assert set(REQUIRED_CATEGORIES).issubset(body["inbox"])


def test_send_uses_wellness_env_not_crypto_env(monkeypatch):
    monkeypatch.setenv("WELLNESS_ALERT_WEBHOOK_URL", "https://example.test/wellness-env")
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://example.test/crypto-env")

    def opener(request, timeout=15):
        assert request.full_url == "https://example.test/wellness-env"
        return _FakeResponse()

    result = send_alert(_order_alert(), opener=opener)
    assert result.destination == "https://example.test/wellness-env"


def test_send_without_wellness_webhook_raises(monkeypatch):
    monkeypatch.delenv("WELLNESS_ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://example.test/crypto-env")
    with pytest.raises(NotifyError, match="WELLNESS_ALERT_WEBHOOK_URL"):
        send_alert(_order_alert(), webhook_url=None)
