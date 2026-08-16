import json

import pytest

from truehold.crypto_agent.catalyst import _reject_wellness_mix, load_current_catalyst
from truehold.crypto_agent.compose import compose_alert, format_alert
from truehold.crypto_agent.models import AlertTrigger
from truehold.crypto_agent.notify import alert_payload


WELLNESS_PHRASES = (
    "TrueHold Wellness",
    "peptide",
    "fulfillment",
    "connected inbox",
    "cancellation/refund",
    "Business:",
)


def test_business_trigger_is_rejected():
    with pytest.raises(ValueError, match="Unknown trigger type"):
        AlertTrigger(type="business", headline="TrueHold Wellness business inbox")


def test_catalyst_loader_rejects_wellness_fields():
    with pytest.raises(ValueError, match="Wellness/business"):
        _reject_wellness_mix({"business": "order update", "kind": "x"})


def test_catalyst_loader_rejects_wellness_phrasing():
    with pytest.raises(ValueError, match="Wellness content"):
        _reject_wellness_mix({"summary": "No new TrueHold Wellness order"})


def test_crypto_alerts_never_include_wellness_content():
    briefing = load_current_catalyst()
    assert not hasattr(briefing, "business")
    for trigger_type, headline in (
        ("geopolitical_catalyst", "geopolitical / market catalyst"),
        ("btc_threshold", "BTC threshold"),
        ("capital_regime", "capital-regime transition"),
        ("macro_liquidity", "Macro Liquidity"),
        ("manual", "manual alert"),
    ):
        alert = compose_alert(AlertTrigger(type=trigger_type, headline=headline, detail="x"))
        payload = alert_payload(alert)
        blob = json.dumps(payload) + format_alert(alert)
        for phrase in WELLNESS_PHRASES:
            assert phrase not in blob, f"{trigger_type} leaked {phrase!r}"
        assert payload["source"] == "truehold-crypto-agent"
        assert payload["agent"] == "truehold-crypto-agent"
        assert "business" not in payload["catalyst"]
        assert "wellness" not in json.dumps(payload).lower()
