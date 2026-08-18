"""Per-chat conversation session for TrueHold Wellness Telegram.

A session starts on /start (or first message). The introduction plays once
per session, when the visitor sends a salutation. File is gitignored.
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
        entry = {"started_at": 0, "intro_at": 0, "prompted": False}
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
    state["chats"][chat_id] = {"started_at": now, "intro_at": 0, "prompted": True}
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


def ensure_session(chat_id: str) -> dict:
    chat_id = str(chat_id)
    now = time.time()
    state = _load()
    entry = _chat(state, chat_id)
    if _expired(entry, now):
        entry["started_at"] = now
        entry["intro_at"] = 0
        entry["prompted"] = False
        _save(state)
    return entry
