import json

import pytest

from truehold.crypto_agent.cli import main


def test_compose_prints_catalyst(capsys):
    assert main(["compose"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Alert — geopolitical / market catalyst")
    assert "Strait of Hormuz" in out
    assert "Watch next:" in out


def test_compose_json_includes_catalyst_fields(capsys):
    assert main(["compose", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["catalyst"]["kind"] == "geopolitical_market_catalyst"
    assert "business" not in payload["catalyst"]
    assert "TrueHold Wellness" not in json.dumps(payload)


def test_compose_btc_alert_still_includes_catalyst(capsys):
    assert main(["compose", "--type", "btc_threshold", "--detail", "BTC crossed $65K"]) == 0
    out = capsys.readouterr().out
    assert "TrueHold crypto alert — BTC threshold" in out
    assert "BTC crossed $65K" in out
    assert "Alert — geopolitical / market catalyst" in out


def test_send_dry_run(capsys):
    assert main(["send", "--dry-run", "--type", "macro_liquidity"]) == 0
    captured = capsys.readouterr()
    assert "Alert — geopolitical / market catalyst" in captured.out
    assert "dry-run" in captured.err


def test_send_without_webhook_fails(capsys, monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    assert main(["send", "--type", "manual"]) == 1
    err = capsys.readouterr().err
    assert "ALERT_WEBHOOK_URL" in err


def test_cli_rejects_wellness_business_trigger():
    with pytest.raises(SystemExit):
        main(["compose", "--type", "business"])
