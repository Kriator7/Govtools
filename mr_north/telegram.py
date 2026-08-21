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
CHAT_FILE_NAME = "telegram_chat.json"
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


def configured_chat_id() -> str:
    env = (os.environ.get(CHAT_ENV) or "").strip()
    if env:
        return env
    path = chat_file_path()
    if not path.is_file():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(payload.get("chat_id") or "").strip()


def save_chat_id(chat_id: str, *, username: str = "") -> Path:
    path = chat_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"chat_id": str(chat_id), "bot": username, "agent": "mr-north"},
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
                    "(your numeric Telegram user id from @userinfobot, or the group id)."
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
