"""Immediate BTC / market watch for Mr North.

CoinGecko simple price (no key):
https://docs.coingecko.com/reference/simple-price
GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd

North must catch market changes as soon as they print, then fan the
alert to every configured Telegram chat (same destinations as hourly).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from mr_north.compose import compose_alert, format_alert
from mr_north.envfile import PACKAGE_ROOT, load_local_env
from mr_north.models import AlertTrigger
from mr_north.notify import NotifyError, send_alert

COINGECKO_PRICE_URL = (
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
)
USER_AGENT = "mr-north/0.1 (TrueHold crypto watch)"
BTC_WATCH_USD = 65_000.0
MOVE_PCT = 2.0
LAST_MARKET_NAME = "last_market.json"
DEFAULT_TIMEOUT_SECONDS = 15


def last_market_path() -> Path:
    override = os.environ.get("NORTH_MARKET_LAST_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / LAST_MARKET_NAME


def _load_state() -> dict[str, Any]:
    path = last_market_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_state(payload: dict[str, Any]) -> Path:
    path = last_market_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def fetch_btc_usd(
    *,
    opener: Callable[..., Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> float:
    request = urllib.request.Request(
        COINGECKO_PRICE_URL,
        method="GET",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    get = opener or urllib.request.urlopen
    try:
        with get(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"CoinGecko BTC price failed: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("CoinGecko BTC price returned non-JSON") from exc
    price = ((data.get("bitcoin") or {}).get("usd"))
    try:
        value = float(price)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("CoinGecko BTC price missing bitcoin.usd") from exc
    if value <= 0:
        raise RuntimeError("CoinGecko BTC price was not positive")
    return value


def change_reason(price: float, state: dict[str, Any]) -> str:
    """Return why North should fire now, or empty if the print is unchanged."""
    last_price = state.get("last_price")
    last_alert = state.get("last_alert_price")
    try:
        last_price_f = float(last_price) if last_price is not None else None
    except (TypeError, ValueError):
        last_price_f = None
    try:
        last_alert_f = float(last_alert) if last_alert is not None else None
    except (TypeError, ValueError):
        last_alert_f = None
    if last_price_f is None:
        if price >= BTC_WATCH_USD:
            return f"BTC is at/above the ${BTC_WATCH_USD:,.0f} watch level on first print."
        return ""
    crossed_up = last_price_f < BTC_WATCH_USD <= price
    crossed_down = last_price_f >= BTC_WATCH_USD > price
    if crossed_up:
        return (
            f"BTC crossed the ${BTC_WATCH_USD:,.0f} watch level upward "
            f"(was ${last_price_f:,.0f})."
        )
    if crossed_down:
        return (
            f"BTC fell back through the ${BTC_WATCH_USD:,.0f} watch level "
            f"(was ${last_price_f:,.0f})."
        )
    baseline = last_alert_f if last_alert_f else last_price_f
    if baseline > 0:
        move = abs(price / baseline - 1.0) * 100.0
        if move >= MOVE_PCT:
            direction = "up" if price > baseline else "down"
            return (
                f"BTC moved {move:.1f}% {direction} from the last North mark "
                f"(${baseline:,.0f})."
            )
    return ""


def run_market_watch(
    *,
    dry_run: bool = False,
    webhook_url: str | None = None,
    fetch: Callable[..., float] | None = None,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Fetch BTC, alert both Telegram chats immediately on a material change."""
    load_local_env()
    price = (fetch or (lambda: fetch_btc_usd(opener=opener)))()
    state = _load_state()
    reason = change_reason(price, state)
    record = {
        "last_price": price,
        "last_alert_price": state.get("last_alert_price"),
        "watch_usd": BTC_WATCH_USD,
        "move_pct": MOVE_PCT,
        "source": "coingecko",
        "pid": os.getpid(),
        "agent": "mr-north",
    }
    if not reason:
        _save_state(record)
        return {
            "ok": True,
            "action": "market-watch",
            "delivered": False,
            "reason": "unchanged",
            "price": price,
            "text": "",
        }
    detail = (
        f"BTC is ${price:,.0f} USD. {reason} "
        f"Watch level ~${BTC_WATCH_USD:,.0f}."
    )
    alert = compose_alert(
        AlertTrigger(
            type="btc_threshold",
            headline="BTC market change",
            detail=detail.strip(),
        )
    )
    text = format_alert(alert)
    try:
        result = send_alert(alert, webhook_url=webhook_url, dry_run=dry_run)
    except NotifyError as exc:
        record["reason"] = str(exc)
        _save_state(record)
        return {
            "ok": False,
            "action": "market-watch",
            "delivered": False,
            "reason": str(exc),
            "price": price,
            "text": text,
        }
    record["last_alert_price"] = price
    record["destination"] = result.destination
    _save_state(record)
    return {
        "ok": True,
        "action": "market-watch",
        "delivered": result.delivered,
        "dry_run": result.dry_run,
        "reason": reason,
        "price": price,
        "destination": result.destination,
        "text": text,
    }
