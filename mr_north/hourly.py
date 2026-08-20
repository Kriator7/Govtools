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


def hourly_loop(
    *,
    interval_seconds: int = HOUR_SECONDS,
    max_iterations: int | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> int:
    """Run forever. Interval default 3600s. Restarts are the caller's job.

    BLS fetch failures are recorded and the loop sleeps the full interval
    instead of exiting (which would restart-spam the public API).
    """
    sleep = sleeper or time.sleep
    last_ok = False
    n = 0
    while True:
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
        line = {k: v for k, v in result.items() if k != "text"}
        print(json.dumps(line), flush=True)
        n += 1
        if max_iterations is not None and n >= max_iterations:
            return 0 if last_ok else 1
        sleep(max(60, interval_seconds))
