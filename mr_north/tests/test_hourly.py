import json
from datetime import datetime, timezone

from mr_north.bls import BlsSnapshot, SeriesPrint
from mr_north.cli import main
from mr_north.envfile import PACKAGE_ROOT
from mr_north.hourly import hourly_loop, run_catalyst_report, run_hourly


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


def test_hourly_without_destination_records_not_delivered(tmp_path, monkeypatch):
    monkeypatch.setenv("NORTH_HOURLY_HEARTBEAT_PATH", str(tmp_path / "hb.json"))
    monkeypatch.setenv("NORTH_HOURLY_LAST_PATH", str(tmp_path / "last.json"))
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("NORTH_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("NORTH_TELEGRAM_CHAT_ID", raising=False)
    result = run_hourly(fetch=_snapshot)
    assert result["ok"] is False
    assert "NORTH_TELEGRAM_BOT_TOKEN" in result["reason"]
    heartbeat = json.loads((tmp_path / "hb.json").read_text(encoding="utf-8"))
    assert heartbeat["delivered"] is False
    assert main(["hourly-status"]) == 1


def test_hourly_delivers_to_north_telegram(tmp_path, monkeypatch):
    monkeypatch.setenv("NORTH_HOURLY_HEARTBEAT_PATH", str(tmp_path / "hb.json"))
    monkeypatch.setenv("NORTH_HOURLY_LAST_PATH", str(tmp_path / "last.json"))
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("NORTH_TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("NORTH_TELEGRAM_CHAT_ID", "99")
    captured = {}

    class _FakeNorth:
        def assert_identity(self):
            return "Mr_North_bot"

        def send_report(self, chat_id, text):
            captured["chat_id"] = chat_id
            captured["text"] = text
            return ["7"]

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    result = run_hourly(fetch=_snapshot)
    assert result["ok"] is True
    assert result["delivered"] is True
    assert result["destination"] == "telegram:@Mr_North_bot:99"
    assert captured["chat_id"] == "99"
    assert "Unemployment rate" in captured["text"]
    assert "TrueHold Wellness" not in captured["text"]
    assert main(["hourly-status"]) == 0


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


def test_hourly_fans_out_to_both_chats(tmp_path, monkeypatch):
    monkeypatch.setenv("NORTH_HOURLY_HEARTBEAT_PATH", str(tmp_path / "hb.json"))
    monkeypatch.setenv("NORTH_HOURLY_LAST_PATH", str(tmp_path / "last.json"))
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
            return ["7"]

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    result = run_hourly(fetch=_snapshot)
    assert result["ok"] is True
    assert captured["chats"] == ["111", "-1003939359929"]
    assert "Unemployment rate" in captured["text"]
    assert "Strait of Hormuz" in captured["text"]


def test_catalyst_report_is_the_larger_briefing(monkeypatch):
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
            return ["3"]

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    result = run_catalyst_report()
    assert result["ok"] is True
    assert result["action"] == "catalyst"
    assert captured["chats"] == ["111", "-1003939359929"]
    assert result["text"].startswith("Alert — geopolitical / market catalyst")
    assert "Strait of Hormuz" in result["text"]
    assert "TrueHold Wellness" not in result["text"]
