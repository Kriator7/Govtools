import json
from datetime import datetime, timezone

from mr_north.bls import BlsSnapshot, SeriesPrint
from mr_north.cli import main
from mr_north.envfile import PACKAGE_ROOT
from mr_north.hourly import hourly_loop, run_hourly


def _snapshot() -> BlsSnapshot:
    return BlsSnapshot(
        fetched_at=datetime(2026, 8, 20, 16, 0, tzinfo=timezone.utc),
        prints=(
            SeriesPrint(
                series_id="LNS14000000",
                label="Unemployment rate (SA)",
                unit="percent",
                year="2026",
                period="M07",
                period_name="July",
                value=4.1,
                previous_value=4.2,
                yoy_value=4.2,
            ),
        ),
        fingerprint="LNS14000000:2026M07:4.1",
    )


def test_hourly_dry_run_writes_bls_breakdown(tmp_path, monkeypatch):
    monkeypatch.setenv("NORTH_HOURLY_HEARTBEAT_PATH", str(tmp_path / "hb.json"))
    monkeypatch.setenv("NORTH_HOURLY_LAST_PATH", str(tmp_path / "last.json"))
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    result = run_hourly(dry_run=True, fetch=_snapshot)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["delivered"] is False
    assert "Unemployment rate" in result["text"]
    assert "Strait of Hormuz" in result["text"]
    assert "TrueHold Wellness" not in result["text"]
    saved = json.loads((tmp_path / "last.json").read_text(encoding="utf-8"))
    assert saved["fingerprint"] == "LNS14000000:2026M07:4.1"


def test_hourly_without_webhook_records_not_delivered(tmp_path, monkeypatch):
    monkeypatch.setenv("NORTH_HOURLY_HEARTBEAT_PATH", str(tmp_path / "hb.json"))
    monkeypatch.setenv("NORTH_HOURLY_LAST_PATH", str(tmp_path / "last.json"))
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    result = run_hourly(fetch=_snapshot)
    assert result["ok"] is False
    assert "ALERT_WEBHOOK_URL" in result["reason"]
    heartbeat = json.loads((tmp_path / "hb.json").read_text(encoding="utf-8"))
    assert heartbeat["delivered"] is False
    assert main(["hourly-status"]) == 1


def test_package_root_is_mr_north():
    assert PACKAGE_ROOT.name == "mr_north"
    assert (PACKAGE_ROOT / "hourly.py").is_file()
    assert (PACKAGE_ROOT / ".env.example").is_file()


def test_hourly_loop_survives_fetch_error(tmp_path, monkeypatch):
    monkeypatch.setenv("NORTH_HOURLY_HEARTBEAT_PATH", str(tmp_path / "hb.json"))
    monkeypatch.setenv("NORTH_HOURLY_LAST_PATH", str(tmp_path / "last.json"))

    def boom():
        raise RuntimeError("BLS down")

    monkeypatch.setattr("mr_north.hourly.run_hourly", boom)
    assert hourly_loop(interval_seconds=60, max_iterations=1, sleeper=lambda _: None) == 1
    heartbeat = json.loads((tmp_path / "hb.json").read_text(encoding="utf-8"))
    assert heartbeat["delivered"] is False
    assert "BLS down" in heartbeat["reason"]


def test_hourly_cli_dry_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NORTH_HOURLY_HEARTBEAT_PATH", str(tmp_path / "hb.json"))
    monkeypatch.setenv("NORTH_HOURLY_LAST_PATH", str(tmp_path / "last.json"))
    monkeypatch.setattr("mr_north.hourly.fetch_snapshot", _snapshot)
    assert main(["hourly", "--dry-run"]) == 0
    captured = capsys.readouterr()
    assert "Bureau of Labor Statistics" in captured.out
    assert "dry-run" in captured.err
