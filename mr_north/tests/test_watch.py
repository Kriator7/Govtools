from mr_north.watch import BTC_WATCH_USD, change_reason, run_market_watch


def test_first_print_below_watch_is_silent():
    assert change_reason(63_000, {}) == ""


def test_first_print_at_watch_fires():
    reason = change_reason(65_000, {})
    assert "watch level" in reason.lower()


def test_cross_up_and_down_fire():
    up = change_reason(65_100, {"last_price": 63_000})
    assert "upward" in up
    down = change_reason(64_000, {"last_price": 65_200})
    assert "fell back" in down


def test_two_percent_move_from_last_alert_fires():
    reason = change_reason(66_300, {"last_price": 65_000, "last_alert_price": 65_000})
    assert "2." in reason or "moved" in reason.lower()


def test_small_move_is_unchanged():
    assert change_reason(65_200, {"last_price": 65_000, "last_alert_price": 65_000}) == ""


def test_market_watch_sends_to_both_chats(tmp_path, monkeypatch):
    monkeypatch.setenv("NORTH_MARKET_LAST_PATH", str(tmp_path / "last_market.json"))
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
            return ["9"]

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    result = run_market_watch(fetch=lambda: BTC_WATCH_USD)
    assert result["ok"] is True
    assert result["delivered"] is True
    assert captured["chats"] == ["111", "-1003939359929"]
    assert "65000" in captured["text"] or "65,000" in captured["text"]
    assert "Strait of Hormuz" in captured["text"]
    assert "TrueHold Wellness" not in captured["text"]


def test_market_watch_unchanged_does_not_send(tmp_path, monkeypatch):
    monkeypatch.setenv("NORTH_MARKET_LAST_PATH", str(tmp_path / "last_market.json"))
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    (tmp_path / "last_market.json").write_text(
        '{"last_price": 63000, "last_alert_price": null}',
        encoding="utf-8",
    )
    called = {"n": 0}

    class _FakeNorth:
        def assert_identity(self):
            called["n"] += 1
            return "Mr_North_bot"

        def send_report(self, chat_id, text):
            called["n"] += 1
            return ["9"]

    monkeypatch.setattr("mr_north.notify.live_client", lambda opener=None: _FakeNorth())
    result = run_market_watch(fetch=lambda: 63_100)
    assert result["ok"] is True
    assert result["delivered"] is False
    assert result["reason"] == "unchanged"
    assert called["n"] == 0
