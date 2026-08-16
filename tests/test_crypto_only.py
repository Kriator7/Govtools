import json

import pytest

from mr_north.catalyst import _reject_foreign_mix, load_current_catalyst
from mr_north.compose import compose_alert, format_alert
from mr_north.models import AlertTrigger
from mr_north.notify import alert_payload


FOREIGN_PHRASES = (
    "TrueHold Wellness",
    "peptide",
    "fulfillment",
    "connected inbox",
    "cancellation/refund",
    "Business:",
)


def test_business_trigger_is_rejected():
    with pytest.raises(ValueError, match="Unknown Mr North trigger type"):
        AlertTrigger(type="business", headline="business inbox")


def test_catalyst_loader_rejects_wellness_fields():
    with pytest.raises(ValueError, match="TrueHold Wellness fields"):
        _reject_foreign_mix({"business": "order update", "kind": "x"})


def test_catalyst_loader_rejects_wellness_phrasing():
    with pytest.raises(ValueError, match="TrueHold Wellness content"):
        _reject_foreign_mix({"summary": "No new TrueHold Wellness order"})


def test_mr_north_alerts_never_include_wellness_content():
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
        for phrase in FOREIGN_PHRASES:
            assert phrase not in blob, f"{trigger_type} leaked {phrase!r}"
        assert payload["source"] == "mr-north"
        assert payload["agent"] == "mr-north"
        assert "business" not in payload["catalyst"]
        assert "wellness" not in json.dumps(payload).lower()
