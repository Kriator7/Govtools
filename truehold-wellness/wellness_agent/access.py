"""Staff-only access for TrueHold Wellness. No Telegram command can grant admin.

Fail-closed:
- /start never grants staff
- /staff, /admin, /operator, and /grant never grant staff
- Staff IDs come only from the process environment
- Privileged commands run only in a private chat whose from.id is allowlisted
- Group chats never receive /inbox (that would leak to every member)

https://core.telegram.org/bots/api
"""

from __future__ import annotations

import os

STAFF_DENIED = "That command is for TrueHold staff only."
PRIVILEGED_COMMANDS = frozenset(
    {"inbox", "stock", "staff", "operator", "admin", "grant", "promo"}
)


def _positive_telegram_id(value: str | None) -> str | None:
    text = str(value or "").strip()
    if text.isdigit() and int(text) > 0:
        return text
    return None


def env_staff_user_ids() -> set[str]:
    """Allowlist from env only. operator.json and Telegram claims are ignored."""
    ids: set[str] = set()
    raw = os.environ.get("WELLNESS_OPERATOR_USER_IDS") or ""
    for part in raw.split(","):
        parsed = _positive_telegram_id(part)
        if parsed:
            ids.add(parsed)
    for key in ("WELLNESS_TELEGRAM_CHAT_ID", "TELEGRAM_OPERATOR_CHAT_ID"):
        parsed = _positive_telegram_id(os.environ.get(key) or "")
        if parsed:
            ids.add(parsed)
    return ids


def staff_notify_chat_ids() -> list[str]:
    """Private-chat destinations for order/email alerts. Negative (group) ids are dropped."""
    return sorted(env_staff_user_ids(), key=int)


def is_operator(
    user_id: str | None,
    chat_id: str | None,
    chat_type: str | None = None,
) -> bool:
    """True only for an allowlisted user talking 1:1 with the bot."""
    user_id = _positive_telegram_id(user_id)
    chat_id = _positive_telegram_id(chat_id)
    if not user_id or not chat_id:
        return False
    if (chat_type or "private") != "private":
        return False
    if user_id != chat_id:
        return False
    return user_id in env_staff_user_ids()
