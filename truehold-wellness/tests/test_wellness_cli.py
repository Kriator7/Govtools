import json

import pytest

from wellness_agent.cli import main
from wellness_agent.models import REQUIRED_CATEGORIES


def test_compose_prints_full_inbox(capsys):
    assert main(["compose"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("TrueHold Wellness — business inbox")
    assert "Business:" in out
    assert "Orders:" in out
    assert "peptide message" in out
    assert "cancellation/refund" in out


def test_compose_json_includes_all_categories(capsys):
    assert main(["compose", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["agent"] == "truehold-wellness-agent"
    for name in REQUIRED_CATEGORIES:
        assert name in payload["inbox"]


def test_compose_peptide_alert_still_includes_snapshot(capsys):
    assert main(["compose", "--type", "peptide", "--detail", "New peptide message"]) == 0
    out = capsys.readouterr().out
    assert "TrueHold Wellness alert — peptide message" in out
    assert "New peptide message" in out
    assert "TrueHold Wellness — business inbox" in out


def test_send_dry_run(capsys):
    assert main(["send", "--dry-run", "--type", "fulfillment"]) == 0
    captured = capsys.readouterr()
    assert "TrueHold Wellness — business inbox" in captured.out
    assert "dry-run" in captured.err


def test_send_without_webhook_fails(capsys, monkeypatch):
    monkeypatch.delenv("WELLNESS_ALERT_WEBHOOK_URL", raising=False)
    assert main(["send", "--type", "order"]) == 1
    err = capsys.readouterr().err
    assert "WELLNESS_ALERT_WEBHOOK_URL" in err


def test_cli_rejects_crypto_trigger():
    with pytest.raises(SystemExit):
        main(["compose", "--type", "btc_threshold"])


def test_whoami_requires_live_token(capsys, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MODE", "mock")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert main(["whoami"]) == 1
    assert "THWellness_bot" in capsys.readouterr().err
