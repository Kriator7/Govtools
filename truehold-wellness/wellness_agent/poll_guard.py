"""Keep @THWellness_bot polling. Orders are missed if getUpdates stops.

Telegram long polling: https://core.telegram.org/bots/api#getupdates
Only one getUpdates client may run per bot token.
"""

from __future__ import annotations

import fcntl
import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from wellness_agent.envfile import PACKAGE_ROOT
from wellness_agent.identity import REQUIRED_USERNAME

STALE_AFTER_SECONDS = 90
RunPoll = Callable[..., int]


def lock_path() -> Path:
    override = os.environ.get("WELLNESS_POLL_LOCK_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / "telegram_poll.lock"


def heartbeat_path() -> Path:
    override = os.environ.get("WELLNESS_POLL_HEARTBEAT_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / "telegram_poll.heartbeat.json"


def write_heartbeat(*, offset: int | None, extra: dict[str, Any] | None = None) -> Path:
    path = heartbeat_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "at": time.time(),
        "bot": f"@{REQUIRED_USERNAME}",
        "offset": offset,
        "pid": os.getpid(),
    }
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def poll_status(*, now: float | None = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    path = heartbeat_path()
    if not path.is_file():
        return {"ok": False, "bot": f"@{REQUIRED_USERNAME}", "reason": "no-heartbeat"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "bot": f"@{REQUIRED_USERNAME}", "reason": "bad-heartbeat"}
    at = float(payload.get("at") or 0)
    age = max(0.0, now - at)
    ok = at > 0 and age <= STALE_AFTER_SECONDS
    return {
        "ok": ok,
        "bot": payload.get("bot") or f"@{REQUIRED_USERNAME}",
        "age_seconds": round(age, 1),
        "offset": payload.get("offset"),
        "pid": payload.get("pid"),
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "reason": None if ok else "stale-heartbeat",
    }


def _acquire_lock(handle) -> bool:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def supervise(run_poll: RunPoll, *, once: bool = False) -> int:
    """Run the poller. If it returns or crashes, start it again.

    --once skips the keeper so tests can take a single getUpdates.
    """
    if once:
        return run_poll(once=True)
    path = lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    failures = 0
    while True:
        if not _acquire_lock(handle):
            sys.stderr.write(
                json.dumps(
                    {
                        "ok": False,
                        "waiting": True,
                        "bot": f"@{REQUIRED_USERNAME}",
                        "reason": "another poller holds the lock",
                    }
                )
                + "\n"
            )
            sys.stderr.flush()
            time.sleep(15)
            continue
        started = time.monotonic()
        try:
            write_heartbeat(offset=None, extra={"state": "starting"})
            code = run_poll(once=False)
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            sys.stderr.write(json.dumps({"ok": False, "restarting": True, "error": str(exc)}) + "\n")
            sys.stderr.flush()
            code = 1
        elapsed = time.monotonic() - started
        failures = 0 if elapsed > 30 else failures + 1
        delay = min(30, 2 * (2 ** min(failures, 4)))
        sys.stderr.write(
            json.dumps(
                {
                    "ok": False,
                    "restarting": True,
                    "exit": code,
                    "delay_seconds": delay,
                    "bot": f"@{REQUIRED_USERNAME}",
                }
            )
            + "\n"
        )
        sys.stderr.flush()
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        time.sleep(delay)
