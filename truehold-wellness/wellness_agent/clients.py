"""Client phone records for TrueHold Wellness call-back, consult, and documentation.

Telegram does not expose a user's phone unless they share it
(KeyboardButton request_contact: https://core.telegram.org/bots/api#keyboardbutton).
If that share is missing, the bot asks them to type the number.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from wellness_agent.envfile import PACKAGE_ROOT


def clients_path() -> Path:
    override = os.environ.get("WELLNESS_CLIENTS_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / "clients.json"


def _load() -> dict[str, Any]:
    path = clients_path()
    if not path.is_file():
        return {"clients": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"clients": {}}
    clients = payload.get("clients") if isinstance(payload, dict) else None
    if not isinstance(clients, dict):
        return {"clients": {}}
    return {"clients": clients}


def _save(payload: dict[str, Any]) -> None:
    path = clients_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_phone(text: str | None) -> str | None:
    """Normalize a typed or shared number. Returns E.164-ish +digits or None."""
    raw = str(text or "").strip()
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if 11 <= len(digits) <= 15:
        return f"+{digits}"
    return None


def get_client(chat_id: str) -> dict[str, Any]:
    return dict(_load()["clients"].get(str(chat_id)) or {})


def client_phone(chat_id: str) -> str | None:
    phone = str(get_client(chat_id).get("phone") or "").strip()
    return phone or None


def save_client_phone(
    chat_id: str,
    phone: str,
    *,
    source: str,
    user_id: str | None = None,
    name: str | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    normalized = parse_phone(phone)
    if not normalized:
        raise ValueError("Need a valid phone number to call this client.")
    state = _load()
    entry = dict(state["clients"].get(str(chat_id)) or {})
    entry.update(
        {
            "chat_id": str(chat_id),
            "user_id": str(user_id or entry.get("user_id") or chat_id),
            "phone": normalized,
            "phone_source": source,
            "name": (name or entry.get("name") or "").strip(),
            "username": (username or entry.get("username") or "").strip(),
            "updated_at": int(time.time()),
        }
    )
    state["clients"][str(chat_id)] = entry
    _save(state)
    return entry


def phone_line_for_staff(chat_id: str) -> str:
    phone = client_phone(chat_id)
    if phone:
        return (
            f"Client phone: {phone}. Call to confirm, consult, and complete required documentation. "
            "Las Vegas residents only. Dry vials only."
        )
    return (
        "Client phone: not on file. Ask the client for a number so the team can call "
        "to confirm, consult, and complete required documentation. "
        "Las Vegas residents only. Dry vials only."
    )
