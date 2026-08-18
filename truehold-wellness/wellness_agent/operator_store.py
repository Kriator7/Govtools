"""Persist TrueHold Wellness staff chats/user ids for order and email-reflex alerts.

Customers are never written here. Only /staff <token> or env allowlists grant access.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from wellness_agent.envfile import PACKAGE_ROOT


def operator_path() -> Path:
    override = os.environ.get("WELLNESS_OPERATOR_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / "operator.json"


def _load_state() -> dict:
    path = operator_path()
    if not path.is_file():
        return {"chat_ids": [], "user_ids": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"chat_ids": [], "user_ids": []}
    if not isinstance(payload, dict):
        return {"chat_ids": [], "user_ids": []}
    return payload


def _save_state(chats: list[str], users: list[str]) -> None:
    path = operator_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"chat_ids": chats, "user_ids": users, "bot": "THWellness_bot"},
            indent=2,
        ),
        encoding="utf-8",
    )


def load_operator_chats() -> list[str]:
    chats = _load_state().get("chat_ids") or []
    return [str(item) for item in chats if str(item).strip()]


def load_operator_user_ids() -> list[str]:
    users = _load_state().get("user_ids") or []
    return [str(item) for item in users if str(item).strip()]


def remember_operator(chat_id: str | None = None, user_id: str | None = None) -> list[str]:
    chats = load_operator_chats()
    users = load_operator_user_ids()
    chat_id = str(chat_id or "").strip()
    user_id = str(user_id or "").strip()
    changed = False
    if chat_id and chat_id not in chats:
        chats.append(chat_id)
        changed = True
    if user_id and user_id not in users:
        users.append(user_id)
        changed = True
    if changed:
        _save_state(chats, users)
    return chats


def configured_operator_chats() -> list[str]:
    chats: list[str] = []
    for key in ("WELLNESS_TELEGRAM_CHAT_ID", "TELEGRAM_OPERATOR_CHAT_ID"):
        value = (os.environ.get(key) or "").strip()
        if value:
            chats.append(value)
    chats.extend(load_operator_chats())
    chats.extend(load_operator_user_ids())
    seen: set[str] = set()
    ordered: list[str] = []
    for chat_id in chats:
        if chat_id not in seen:
            seen.add(chat_id)
            ordered.append(chat_id)
    return ordered
