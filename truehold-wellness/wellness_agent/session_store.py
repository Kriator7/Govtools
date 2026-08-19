"""Per-chat conversation session for TrueHold Wellness Telegram.

A session starts on /start (or first message). /start and the first hello
play the introduction with the official logo. File is gitignored.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from wellness_agent.envfile import PACKAGE_ROOT

SESSION_SECONDS = 12 * 60 * 60


def session_path() -> Path:
    override = os.environ.get("WELLNESS_SESSION_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / "sessions.json"


def _load() -> dict:
    path = session_path()
    if not path.is_file():
        return {"chats": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"chats": {}}
    chats = payload.get("chats") if isinstance(payload, dict) else None
    if not isinstance(chats, dict):
        return {"chats": {}}
    return {"chats": chats}


def _save(payload: dict) -> None:
    path = session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _chat(state: dict, chat_id: str) -> dict:
    chats = state.setdefault("chats", {})
    entry = chats.get(chat_id)
    if not isinstance(entry, dict):
        entry = {"started_at": 0, "intro_at": 0, "prompted": False, "awaiting_phone": False}
        chats[chat_id] = entry
    return entry


def _expired(entry: dict, now: float) -> bool:
    started = float(entry.get("started_at") or 0)
    return started <= 0 or (now - started) > SESSION_SECONDS


def begin_session(chat_id: str) -> dict:
    """Open a new visit. Introduction has not played yet."""
    chat_id = str(chat_id)
    now = time.time()
    state = _load()
    previous = state["chats"].get(chat_id) if isinstance(state["chats"].get(chat_id), dict) else {}
    saved_code = previous.get("discount_code") if isinstance(previous, dict) else None
    state["chats"][chat_id] = {
        "started_at": now,
        "intro_at": 0,
        "prompted": True,
        "awaiting_phone": False,
        "pending_order": None,
        "discount_code": saved_code,
    }
    _save(state)
    return state["chats"][chat_id]


def intro_pending(chat_id: str) -> bool:
    chat_id = str(chat_id)
    now = time.time()
    state = _load()
    entry = _chat(state, chat_id)
    if _expired(entry, now):
        return True
    return not bool(entry.get("intro_at"))


def mark_intro_played(chat_id: str) -> None:
    chat_id = str(chat_id)
    now = time.time()
    state = _load()
    entry = _chat(state, chat_id)
    if _expired(entry, now) or not entry.get("started_at"):
        entry["started_at"] = now
    entry["intro_at"] = now
    entry["prompted"] = True
    _save(state)


def set_awaiting_phone(chat_id: str, waiting: bool) -> None:
    chat_id = str(chat_id)
    state = _load()
    entry = _chat(state, chat_id)
    entry["awaiting_phone"] = bool(waiting)
    _save(state)


def awaiting_phone(chat_id: str) -> bool:
    return bool(_chat(_load(), str(chat_id)).get("awaiting_phone"))


def set_pending_order(
    chat_id: str,
    product_id: str | None,
    qty: str | None,
    fulfillment: str | None = None,
) -> None:
    chat_id = str(chat_id)
    state = _load()
    entry = _chat(state, chat_id)
    if product_id and qty:
        entry["pending_order"] = {
            "product_id": product_id,
            "qty": qty,
            "fulfillment": fulfillment or "prep",
        }
    else:
        entry["pending_order"] = None
    _save(state)


def set_focus_sku(chat_id: str, product_id: str | None) -> None:
    chat_id = str(chat_id)
    state = _load()
    entry = _chat(state, chat_id)
    entry["focus_sku"] = str(product_id) if product_id else None
    _save(state)


def focus_sku(chat_id: str) -> str | None:
    value = _chat(_load(), str(chat_id)).get("focus_sku")
    return str(value) if value else None


def pending_order(chat_id: str) -> dict | None:
    raw = _chat(_load(), str(chat_id)).get("pending_order")
    return dict(raw) if isinstance(raw, dict) else None


def set_discount_code(chat_id: str, code: str | None) -> None:
    chat_id = str(chat_id)
    state = _load()
    entry = _chat(state, chat_id)
    entry["discount_code"] = str(code).strip().upper() if code else None
    _save(state)


def discount_code(chat_id: str) -> str | None:
    value = _chat(_load(), str(chat_id)).get("discount_code")
    return str(value).strip().upper() if value else None


def set_nav_return(
    chat_id: str,
    *,
    screen: str,
    product_id: str | None = None,
    qty: str | None = None,
) -> None:
    chat_id = str(chat_id)
    state = _load()
    entry = _chat(state, chat_id)
    entry["nav_return"] = {
        "screen": screen,
        "product_id": product_id,
        "qty": qty,
    }
    _save(state)


def nav_return(chat_id: str) -> dict | None:
    raw = _chat(_load(), str(chat_id)).get("nav_return")
    return dict(raw) if isinstance(raw, dict) else None


def ensure_session(chat_id: str) -> dict:
    chat_id = str(chat_id)
    now = time.time()
    state = _load()
    entry = _chat(state, chat_id)
    if _expired(entry, now):
        entry["started_at"] = now
        entry["intro_at"] = 0
        entry["prompted"] = False
        entry["awaiting_phone"] = False
        _save(state)
    return entry
