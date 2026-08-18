"""Persist TrueHold Wellness operator chats for order and email-reflex alerts."""

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


def load_operator_chats() -> list[str]:
    path = operator_path()
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    chats = payload.get("chat_ids") or []
    return [str(item) for item in chats if str(item).strip()]


def remember_operator(chat_id: str) -> list[str]:
    chat_id = str(chat_id).strip()
    chats = load_operator_chats()
    if chat_id and chat_id not in chats:
        chats.append(chat_id)
        path = operator_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"chat_ids": chats, "bot": "THWellness_bot"}, indent=2),
            encoding="utf-8",
        )
    return chats


def configured_operator_chats() -> list[str]:
    chats: list[str] = []
    for key in ("WELLNESS_TELEGRAM_CHAT_ID", "TELEGRAM_OPERATOR_CHAT_ID"):
        value = (os.environ.get(key) or "").strip()
        if value:
            chats.append(value)
    chats.extend(load_operator_chats())
    seen: set[str] = set()
    ordered: list[str] = []
    for chat_id in chats:
        if chat_id not in seen:
            seen.add(chat_id)
            ordered.append(chat_id)
    return ordered
