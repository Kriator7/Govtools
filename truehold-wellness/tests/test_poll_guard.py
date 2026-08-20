from wellness_agent.poll_guard import poll_status, supervise, write_heartbeat
import time


def test_heartbeat_status_ok_then_stale(tmp_path, monkeypatch):
    monkeypatch.setenv("WELLNESS_POLL_HEARTBEAT_PATH", str(tmp_path / "hb.json"))
    write_heartbeat(offset=12, extra={"state": "polling"})
    fresh = poll_status()
    assert fresh["ok"] is True
    assert fresh["offset"] == 12
    stale = poll_status(now=time.time() + 10_000)
    assert stale["ok"] is False
    assert stale["reason"] == "stale-heartbeat"


def test_supervise_restarts_after_crash_then_stops(monkeypatch, tmp_path):
    monkeypatch.setenv("WELLNESS_POLL_LOCK_PATH", str(tmp_path / "lock"))
    monkeypatch.setenv("WELLNESS_POLL_HEARTBEAT_PATH", str(tmp_path / "hb.json"))
    calls = {"n": 0}

    def fake_poll(*, once=False):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("poll crashed")
        raise KeyboardInterrupt()

    monkeypatch.setattr("wellness_agent.poll_guard.time.sleep", lambda _seconds: None)
    assert supervise(fake_poll, once=False) == 0
    assert calls["n"] == 2


def test_supervise_once_does_not_restart():
    calls = {"n": 0}

    def fake_poll(*, once=False):
        calls["n"] += 1
        assert once is True
        return 7

    assert supervise(fake_poll, once=True) == 7
    assert calls["n"] == 1
