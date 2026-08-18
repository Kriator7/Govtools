"""Notify destinations for TrueHold Wellness staff.

Authorization does not read this file. Staff IDs come from env only
(see wellness_agent.access). This module is kept so leftover operator.json
cannot grant /inbox even if present on disk.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from wellness_agent.access import staff_notify_chat_ids
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


def load_operator_chats() -> list[str]:
    chats = _load_state().get("chat_ids") or []
    return [str(item) for item in chats if str(item).strip()]


def load_operator_user_ids() -> list[str]:
    users = _load_state().get("user_ids") or []
    return [str(item) for item in users if str(item).strip()]


def configured_operator_chats() -> list[str]:
    """Env allowlist only. Disk operator.json is not trusted for notify or admin."""
    return staff_notify_chat_ids()
