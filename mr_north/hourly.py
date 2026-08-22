"""Hourly Mr North BLS report: fetch, save, deliver, keep running.

The previous Cursor automation had no in-repo timer and no delivery URL,
so compose could succeed while nothing arrived. This loop is the timer.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

from mr_north.bls import BlsSnapshot, fetch_snapshot, format_breakdown
from mr_north.compose import compose_alert, format_alert
from mr_north.envfile import PACKAGE_ROOT, load_local_env
from mr_north.models import AlertTrigger
from mr_north.notify import NotifyError, send_alert

HOUR_SECONDS = 60 * 60
WATCH_SECONDS = 5 * 60
CATALYST_SECONDS = 6 * 60 * 60
STALE_AFTER_SECONDS = int(HOUR_SECONDS * 1.75)
HEARTBEAT_NAME = "hourly.heartbeat.json"
LAST_REPORT_NAME = "last_hourly.json"


def heartbeat_path() -> Path:
    override = os.environ.get("NORTH_HOURLY_HEARTBEAT_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / HEARTBEAT_NAME


def last_report_path() -> Path:
    override = os.environ.get("NORTH_HOURLY_LAST_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / LAST_REPORT_NAME


def write_heartbeat(payload: dict[str, Any]) -> Path:
    path = heartbeat_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"at": time.time(), "agent": "mr-north", "job": "hourly-bls", **payload}
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return path


def hourly_status(*, now: float | None = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    path = heartbeat_path()
    if not path.is_file():
        return {"ok": False, "agent": "mr-north", "job": "hourly-bls", "reason": "no-heartbeat"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "agent": "mr-north", "job": "hourly-bls", "reason": "bad-heartbeat"}
    at = float(payload.get("at") or 0)
    age = max(0.0, now - at)
    ok = at > 0 and age <= STALE_AFTER_SECONDS and payload.get("delivered") is True
    reason = None
    if at <= 0 or age > STALE_AFTER_SECONDS:
        reason = "stale-heartbeat"
    elif payload.get("delivered") is not True:
        reason = str(payload.get("reason") or "not-delivered")
    return {
        "ok": ok,
        "agent": "mr-north",
        "job": "hourly-bls",
        "age_seconds": round(age, 1),
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "delivered": payload.get("delivered"),
        "fingerprint": payload.get("fingerprint"),
        "reason": reason,
        "pid": payload.get("pid"),
    }


def _previous_fingerprint() -> str:
    path = last_report_path()
    if not path.is_file():
        return ""
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("fingerprint") or "")
    except json.JSONDecodeError:
        return ""


def run_hourly(
    *,
    dry_run: bool = False,
    webhook_url: str | None = None,
    fetch: Callable[..., BlsSnapshot] | None = None,
) -> dict[str, Any]:
    """Fetch official BLS prints, attach the catalyst briefing, and deliver."""
    load_local_env()
    snapshot = (fetch or fetch_snapshot)()
    unchanged = snapshot.fingerprint == _previous_fingerprint()
    detail = format_breakdown(snapshot, unchanged=unchanged)
    alert = compose_alert(
        AlertTrigger(
            type="hourly_bls",
            headline="hourly BLS breakdown",
            detail=detail.strip(),
        )
    )
    text = format_alert(alert)
    record = {
        "fetched_at": snapshot.fetched_at.isoformat(),
        "fingerprint": snapshot.fingerprint,
        "unchanged": unchanged,
        "text": text,
        "source": snapshot.source,
        "pid": os.getpid(),
    }
    last_report_path().parent.mkdir(parents=True, exist_ok=True)
    last_report_path().write_text(json.dumps(record, indent=2), encoding="utf-8")
    try:
        result = send_alert(alert, webhook_url=webhook_url, dry_run=dry_run)
    except NotifyError as exc:
        write_heartbeat({**record, "delivered": False, "reason": str(exc)})
        return {
            "ok": False,
            "action": "hourly-bls",
            "delivered": False,
            "unchanged": unchanged,
            "fingerprint": snapshot.fingerprint,
            "reason": str(exc),
            "text": text,
        }
    write_heartbeat(
        {
            **record,
            "delivered": result.delivered,
            "dry_run": result.dry_run,
            "destination": result.destination,
            "reason": None if result.delivered or result.dry_run else "not-delivered",
        }
    )
    return {
        "ok": True,
        "action": "hourly-bls",
        "delivered": result.delivered,
        "dry_run": result.dry_run,
        "unchanged": unchanged,
        "fingerprint": snapshot.fingerprint,
        "destination": result.destination,
        "text": text,
    }


def run_catalyst_report(
    *,
    dry_run: bool = False,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """Send the larger geopolitical / market catalyst briefing to both chats."""
    load_local_env()
    alert = compose_alert(
        AlertTrigger(
            type="geopolitical_catalyst",
            headline="geopolitical / market catalyst",
            detail="",
        )
    )
    text = format_alert(alert)
    try:
        result = send_alert(alert, webhook_url=webhook_url, dry_run=dry_run)
    except NotifyError as exc:
        return {
            "ok": False,
            "action": "catalyst",
            "delivered": False,
            "reason": str(exc),
            "text": text,
        }
    return {
        "ok": True,
        "action": "catalyst",
        "delivered": result.delivered,
        "dry_run": result.dry_run,
        "destination": result.destination,
        "text": text,
    }


def _in_pytest() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def hourly_loop(
    *,
    interval_seconds: int = HOUR_SECONDS,
    max_iterations: int | None = None,
    sleeper: Callable[[float], None] | None = None,
    watch_seconds: int = WATCH_SECONDS,
    include_watch: bool | None = None,
    include_catalyst: bool | None = None,
) -> int:
    """Run forever. Hourly BLS plus immediate market watches between hours.

    Restarts are the caller's job (`mr_north/scripts/keep_hourly.sh`).
    BLS fetch failures are recorded and the loop continues instead of
    exiting (which would restart-spam the public API).
    """
    sleep = sleeper or time.sleep
    watch = (not _in_pytest()) if include_watch is None else include_watch
    catalyst = (not _in_pytest()) if include_catalyst is None else include_catalyst
    last_ok = False
    n = 0
    last_hourly_at = 0.0
    last_catalyst_at = 0.0
    poll = max(1, watch_seconds if watch else max(60, interval_seconds))

    if not _in_pytest():
        try:
            from mr_north.telegram import destination_map, live_client, north_group_chat_id

            client = live_client()
            client.assert_identity()
            group_id = client.resolve_group_chat_id(north_group_chat_id())
            dest = destination_map()
            dest["group_chat_id"] = group_id or dest.get("group_chat_id")
            print(json.dumps({"ok": True, "action": "destinations", **dest}), flush=True)
        except Exception as exc:
            print(
                json.dumps({"ok": False, "action": "destinations", "reason": str(exc)}),
                flush=True,
            )

    if catalyst:
        try:
            cat = run_catalyst_report()
        except Exception as exc:
            cat = {"ok": False, "action": "catalyst", "delivered": False, "reason": str(exc)}
        print(json.dumps({k: v for k, v in cat.items() if k != "text"}), flush=True)
        last_catalyst_at = time.time()

    while True:
        now = time.time()
        due_hourly = last_hourly_at <= 0 or (now - last_hourly_at) >= interval_seconds
        if due_hourly:
            try:
                result = run_hourly()
            except Exception as exc:
                result = {
                    "ok": False,
                    "action": "hourly-bls",
                    "delivered": False,
                    "reason": str(exc),
                    "pid": os.getpid(),
                }
                write_heartbeat(result)
            last_ok = bool(result.get("ok"))
            last_hourly_at = now
            print(json.dumps({k: v for k, v in result.items() if k != "text"}), flush=True)
            n += 1
            if max_iterations is not None and n >= max_iterations:
                return 0 if last_ok else 1
        if watch:
            try:
                from mr_north.watch import run_market_watch

                watched = run_market_watch()
            except Exception as exc:
                watched = {
                    "ok": False,
                    "action": "market-watch",
                    "delivered": False,
                    "reason": str(exc),
                }
            if watched.get("delivered") or watched.get("reason") not in ("unchanged",):
                print(json.dumps({k: v for k, v in watched.items() if k != "text"}), flush=True)
        if catalyst and last_catalyst_at and (now - last_catalyst_at) >= CATALYST_SECONDS:
            try:
                cat = run_catalyst_report()
            except Exception as exc:
                cat = {"ok": False, "action": "catalyst", "delivered": False, "reason": str(exc)}
            print(json.dumps({k: v for k, v in cat.items() if k != "text"}), flush=True)
            last_catalyst_at = now
        sleep(poll)
