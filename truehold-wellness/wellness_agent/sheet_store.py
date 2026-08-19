"""Remember the last locked-sheet Telegram message per chat and SKU.

Telegram Files lists every document ever sent. We delete the previous copy
before sending a new one so each SKU keeps a single file.

deleteMessage: https://core.telegram.org/bots/api#deletemessage
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from wellness_agent.envfile import PACKAGE_ROOT


def sheet_messages_path() -> Path:
    override = os.environ.get("WELLNESS_SHEET_MESSAGES_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / "sheet_messages.json"


def _load() -> dict:
    path = sheet_messages_path()
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
    path = sheet_messages_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def remember_sheet_message(chat_id: str, sku: str, message_id: str) -> None:
    if not chat_id or not sku or not message_id:
        return
    state = _load()
    chat = state["chats"].setdefault(str(chat_id), {})
    if not isinstance(chat, dict):
        chat = {}
        state["chats"][str(chat_id)] = chat
    chat[str(sku)] = str(message_id)
    _save(state)


def pop_sheet_message(chat_id: str, sku: str) -> str | None:
    state = _load()
    chat = state["chats"].get(str(chat_id))
    if not isinstance(chat, dict):
        return None
    message_id = chat.pop(str(sku), None)
    _save(state)
    return str(message_id) if message_id else None


def replace_prior_sheet(telegram, chat_id: str, sku: str) -> str | None:
    message_id = pop_sheet_message(chat_id, sku)
    if not message_id or not hasattr(telegram, "delete_message"):
        return None
    try:
        telegram.delete_message(chat_id, message_id)
    except Exception:
        return None
    return message_id
