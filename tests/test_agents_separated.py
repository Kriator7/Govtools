import json

import pytest

from truehold.crypto_agent.compose import compose_alert as compose_crypto
from truehold.crypto_agent.models import AlertTrigger as CryptoTrigger
from truehold.crypto_agent.notify import alert_payload as crypto_payload
from truehold.wellness_agent.compose import compose_alert as compose_wellness
from truehold.wellness_agent.models import AlertTrigger as WellnessTrigger
from truehold.wellness_agent.notify import alert_payload as wellness_payload


def test_crypto_trigger_rejected_by_wellness_agent():
    with pytest.raises(ValueError, match="crypto/macro"):
        WellnessTrigger(type="btc_threshold", headline="BTC threshold")


def test_wellness_trigger_rejected_by_crypto_agent():
    with pytest.raises(ValueError, match="Unknown trigger type"):
        CryptoTrigger(type="order", headline="order")


def test_payloads_use_distinct_agent_identities():
    crypto = crypto_payload(
        compose_crypto(CryptoTrigger(type="manual", headline="manual alert"))
    )
    wellness = wellness_payload(
        compose_wellness(WellnessTrigger(type="business", headline="business inbox"))
    )
    assert crypto["agent"] == "truehold-crypto-agent"
    assert wellness["agent"] == "truehold-wellness-agent"
    assert crypto["agent"] != wellness["agent"]
    assert "inbox" not in crypto
    assert "catalyst" not in wellness
    assert "TrueHold Wellness" not in json.dumps(crypto)
    assert "Strait of Hormuz" not in json.dumps(wellness)
    assert "peptide" not in json.dumps(crypto).lower()
