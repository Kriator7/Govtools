"""Staff-only access for TrueHold Wellness. Customers cannot become operators.

Fail-closed: /start never grants admin. Staff must be listed in
WELLNESS_OPERATOR_USER_IDS / WELLNESS_TELEGRAM_CHAT_ID, or claim with
WELLNESS_OPERATOR_CLAIM_TOKEN via /staff <token>.

https://core.telegram.org/bots/api
"""

from __future__ import annotations

import hmac
import os

from wellness_agent.operator_store import (
    configured_operator_chats,
    load_operator_user_ids,
    remember_operator,
)

STAFF_DENIED = "That command is for TrueHold staff only."


def env_operator_ids() -> set[str]:
    ids: set[str] = set()
    raw = os.environ.get("WELLNESS_OPERATOR_USER_IDS") or ""
    for part in raw.split(","):
        value = part.strip()
        if value:
            ids.add(value)
    for key in ("WELLNESS_TELEGRAM_CHAT_ID", "TELEGRAM_OPERATOR_CHAT_ID"):
        value = (os.environ.get(key) or "").strip()
        if value:
            ids.add(value)
    return ids


def is_operator(
    user_id: str | None,
    chat_id: str | None,
    chat_type: str | None = None,
) -> bool:
    """True only for allowlisted staff. Group members are never operators by chat id."""
    user_id = str(user_id or "").strip()
    chat_id = str(chat_id or "").strip()
    allowed = env_operator_ids() | set(load_operator_user_ids()) | set(configured_operator_chats())
    if user_id and user_id in allowed:
        return True
    if (chat_type or "private") != "private":
        return False
    if chat_id and chat_id in allowed and (not user_id or user_id == chat_id):
        return True
    return False


def claim_staff(token: str, *, chat_id: str, user_id: str) -> bool:
    """Grant staff access only when the claim token matches. Never log the token."""
    expected = (os.environ.get("WELLNESS_OPERATOR_CLAIM_TOKEN") or "").strip()
    provided = (token or "").strip()
    user_id = str(user_id or "").strip()
    chat_id = str(chat_id or "").strip()
    if not expected or not provided or not user_id:
        return False
    if len(provided) != len(expected):
        return False
    if not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        return False
    remember_operator(chat_id=chat_id, user_id=user_id)
    return True
