"""Telegram Bot API client for Mr North crypto/BLS reports only.

sendMessage: https://core.telegram.org/bots/api#sendmessage
getMe: https://core.telegram.org/bots/api#getme
getUpdates: https://core.telegram.org/bots/api#getupdates

Never reads TELEGRAM_BOT_TOKEN (Wellness) or the realtor token.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from mr_north.envfile import PACKAGE_ROOT
from mr_north.identity import assert_north_telegram_username

TELEGRAM_API = "https://api.telegram.org"
TOKEN_ENV = "NORTH_TELEGRAM_BOT_TOKEN"
CHAT_ENV = "NORTH_TELEGRAM_CHAT_ID"
GROUP_ENV = "NORTH_TELEGRAM_GROUP_CHAT_ID"
CHATS_ENV = "NORTH_TELEGRAM_CHAT_IDS"
CHAT_FILE_NAME = "telegram_chat.json"
# Documented Mr North BLS / TrueHold crypto group. Never the PirateEye realtor group.
# realtor-agent/README.md on the Damian-group branch: do not use -1003939359929 for PirateEye.
DEFAULT_GROUP_CHAT_ID = "-1003939359929"
FORBIDDEN_CHAT_IDS = frozenset({"-5372586958"})
# sendMessage text limit: https://core.telegram.org/bots/api#sendmessage
MAX_MESSAGE_CHARS = 4096
DEFAULT_TIMEOUT_SECONDS = 15


class TelegramError(RuntimeError):
    """Raised when Telegram Bot API delivery failed."""


def configured_token() -> str:
    return (os.environ.get(TOKEN_ENV) or "").strip()


def chat_file_path() -> Path:
    override = os.environ.get("NORTH_TELEGRAM_CHAT_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / CHAT_FILE_NAME


def _parse_chat_ids(raw: str) -> list[str]:
    ids: list[str] = []
    for part in (raw or "").replace(";", ",").split(","):
        chat_id = part.strip()
        if not chat_id or chat_id in ids or chat_id in FORBIDDEN_CHAT_IDS:
            continue
        ids.append(chat_id)
    return ids


def _default_group_chat_id() -> str:
    """Production default is the North BLS group. Tests must opt in via GROUP_ENV."""
    in_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    if GROUP_ENV in os.environ:
        value = (os.environ.get(GROUP_ENV) or "").strip()
        if value:
            return value
        return "" if in_pytest else DEFAULT_GROUP_CHAT_ID
    if in_pytest:
        return ""
    return DEFAULT_GROUP_CHAT_ID


def _chat_ids_from_file() -> list[str]:
    path = chat_file_path()
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    ids = _parse_chat_ids(str(payload.get("chat_id") or ""))
    extra = payload.get("chat_ids") or []
    if isinstance(extra, str):
        ids.extend(_parse_chat_ids(extra))
    elif isinstance(extra, list):
        for item in extra:
            ids.extend(_parse_chat_ids(str(item)))
    return _parse_chat_ids(",".join(ids))


def configured_chat_ids() -> list[str]:
    """Unique Telegram destinations for every North report (hourly + catalyst + watch)."""
    ids: list[str] = []
    for raw in (
        os.environ.get(CHAT_ENV) or "",
        _default_group_chat_id(),
        os.environ.get(CHATS_ENV) or "",
    ):
        for chat_id in _parse_chat_ids(raw):
            if chat_id not in ids:
                ids.append(chat_id)
    for chat_id in _chat_ids_from_file():
        if chat_id not in ids:
            ids.append(chat_id)
    return ids


def configured_chat_id() -> str:
    ids = configured_chat_ids()
    return ids[0] if ids else ""


def save_chat_id(chat_id: str, *, username: str = "") -> Path:
    path = chat_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _chat_ids_from_file()
    ids = _parse_chat_ids(chat_id)
    for item in existing:
        if item not in ids:
            ids.append(item)
    path.write_text(
        json.dumps(
            {
                "chat_id": ids[0] if ids else str(chat_id),
                "chat_ids": ids,
                "bot": username,
                "agent": "mr-north",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def split_telegram_text(text: str, *, limit: int = MAX_MESSAGE_CHARS) -> list[str]:
    body = (text or "").strip()
    if not body:
        return [""]
    if len(body) <= limit:
        return [body]
    chunks: list[str] = []
    remaining = body
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        window = remaining[:limit]
        cut = window.rfind("\n")
        if cut < limit // 2:
            cut = limit
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks


class NorthTelegram:
    def __init__(
        self,
        bot_token: str,
        *,
        opener: Callable[..., Any] | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not bot_token:
            raise TelegramError(f"{TOKEN_ENV} is required for live Mr North Telegram")
        self.bot_token = bot_token
        self._opener = opener or urllib.request.urlopen
        self.timeout = timeout

    def _url(self, method: str) -> str:
        return f"{TELEGRAM_API}/bot{self.bot_token}/{method}"

    def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self._url(method),
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "mr-north/0.1",
            },
        )
        try:
            with self._opener(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")[:300]
            except Exception:
                detail = str(exc)
            if exc.code == 409 and method == "getUpdates":
                raise TelegramError(
                    "Another app is already polling @Mr_North_bot (Telegram 409). "
                    "That is OK — North only needs sendMessage. Set NORTH_TELEGRAM_CHAT_ID "
                    "and NORTH_TELEGRAM_GROUP_CHAT_ID (numeric user id and/or group ids)."
                ) from exc
            raise TelegramError(f"Telegram {method} failed: HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise TelegramError(f"Telegram {method} failed: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TelegramError(f"Telegram {method} returned non-JSON") from exc
        if not data.get("ok"):
            raise TelegramError(data.get("description") or f"Telegram {method} was not ok")
        return data

    def get_me(self) -> dict[str, Any]:
        return dict((self._post("getMe", {}).get("result") or {}))

    def get_username(self) -> str:
        return str(self.get_me().get("username") or "")

    def assert_identity(self) -> str:
        return assert_north_telegram_username(self.get_username())

    def send_message(self, chat_id: str, text: str) -> dict[str, Any]:
        data = self._post(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
        )
        return {"provider_message_id": str((data.get("result") or {}).get("message_id")), "raw": data}

    def send_report(self, chat_id: str, text: str) -> list[str]:
        ids: list[str] = []
        for chunk in split_telegram_text(text):
            ids.append(str(self.send_message(chat_id, chunk)["provider_message_id"]))
        return ids

    def capture_chat_id(self, *, timeout: int = 30) -> str:
        """One-shot getUpdates to bind the chat that messaged North. Not a poller."""
        data = self._post("getUpdates", {"timeout": timeout, "limit": 20})
        for update in reversed(list(data.get("result") or [])):
            message = update.get("message") or update.get("edited_message") or {}
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            if chat_id is not None:
                return str(chat_id)
        raise TelegramError(
            "No Telegram chat yet. Open North's bot, tap Start, then run telegram-capture again."
        )


def live_client(*, opener: Callable[..., Any] | None = None) -> NorthTelegram:
    token = configured_token()
    if not token:
        raise TelegramError(
            f"No {TOKEN_ENV} configured. Do not use TELEGRAM_BOT_TOKEN (that is @THWellness_bot)."
        )
    return NorthTelegram(token, opener=opener)
