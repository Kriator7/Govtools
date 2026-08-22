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
# Personal operator chat (economics / trading reports to James).
# Overridable with NORTH_TELEGRAM_CHAT_ID.
DEFAULT_OPERATOR_CHAT_ID = "1150046483"
# MaximumMint & North — economics / trading group for @Mr_North_bot.
# Overridable with NORTH_TELEGRAM_GROUP_CHAT_ID.
NORTH_GROUP_TITLE = "MaximumMint & North"
DEFAULT_GROUP_CHAT_ID = "-1003939359929"
# MaximumMint & Agent Real — PirateEye realtor. Never send North reports here.
PIRATEEYE_GROUP_TITLE = "MaximumMint & Agent Real"
PIRATEEYE_GROUP_CHAT_ID = "-5372586958"
FORBIDDEN_CHAT_IDS = frozenset({PIRATEEYE_GROUP_CHAT_ID})
GET_UPDATES_ALLOWED = (
    "message",
    "edited_message",
    "my_chat_member",
    "chat_member",
)
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


def _in_pytest() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def normalize_chat_title(title: str) -> str:
    text = (title or "").strip().lower().replace("&", " and ")
    return " ".join(text.split())


def is_forbidden_group_title(title: str) -> bool:
    normalized = normalize_chat_title(title)
    compact = normalized.replace(" ", "")
    if "pirateeye" in compact:
        return True
    return normalized == normalize_chat_title(PIRATEEYE_GROUP_TITLE)


def is_north_group_title(title: str) -> bool:
    if is_forbidden_group_title(title):
        return False
    return normalize_chat_title(title) == normalize_chat_title(NORTH_GROUP_TITLE)


def is_north_group_chat(chat: dict[str, Any]) -> bool:
    chat_id = str((chat or {}).get("id") or "").strip()
    if not chat_id or chat_id in FORBIDDEN_CHAT_IDS:
        return False
    if is_forbidden_group_title(str((chat or {}).get("title") or "")):
        return False
    chat_type = str((chat or {}).get("type") or "")
    if chat_type not in {"group", "supergroup"}:
        return False
    return is_north_group_title(str((chat or {}).get("title") or ""))


def extract_chats_from_updates(updates: Any) -> list[dict[str, Any]]:
    """Collect chats from messages and membership events (bot added to a group)."""
    chats: list[dict[str, Any]] = []
    if not isinstance(updates, list):
        return chats
    keys = ("message", "edited_message", "channel_post", "my_chat_member", "chat_member")
    for update in updates:
        if not isinstance(update, dict):
            continue
        for key in keys:
            payload = update.get(key)
            if not isinstance(payload, dict):
                continue
            chat = payload.get("chat")
            if isinstance(chat, dict) and chat.get("id") is not None:
                chats.append(chat)
    return chats


def north_group_id_from_updates(updates: Any) -> str:
    for chat in extract_chats_from_updates(updates):
        if is_north_group_chat(chat):
            return str(chat["id"])
    return ""


def operator_chat_id() -> str:
    """Personal destination. Production default is James's Telegram user id."""
    ids = _parse_chat_ids(_default_operator_raw())
    return ids[0] if ids else ""


def north_group_chat_id() -> str:
    """MaximumMint & North. PirateEye's MaximumMint & Agent Real is never used."""
    ids = _parse_chat_ids(_default_group_raw())
    return ids[0] if ids else ""


def _default_operator_raw() -> str:
    env = (os.environ.get(CHAT_ENV) or "").strip()
    if env:
        return env
    return "" if _in_pytest() else DEFAULT_OPERATOR_CHAT_ID


def _default_group_raw() -> str:
    env = (os.environ.get(GROUP_ENV) or "").strip()
    parsed = _parse_chat_ids(env)
    if parsed:
        return parsed[0]
    file_group = _group_chat_id_from_file()
    if file_group:
        return file_group
    # Env was unset, or set only to the forbidden PirateEye id.
    return "" if _in_pytest() else DEFAULT_GROUP_CHAT_ID


def _chat_ids_from_file() -> list[str]:
    path = chat_file_path()
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    ids = _parse_chat_ids(str(payload.get("chat_id") or ""))
    ids.extend(_parse_chat_ids(str(payload.get("group_chat_id") or "")))
    extra = payload.get("chat_ids") or []
    if isinstance(extra, str):
        ids.extend(_parse_chat_ids(extra))
    elif isinstance(extra, list):
        for item in extra:
            ids.extend(_parse_chat_ids(str(item)))
    return _parse_chat_ids(",".join(ids))


def _read_chat_file() -> dict[str, Any]:
    path = chat_file_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _group_chat_id_from_file() -> str:
    payload = _read_chat_file()
    parsed = _parse_chat_ids(str(payload.get("group_chat_id") or ""))
    if parsed:
        return parsed[0]
    for chat_id in _chat_ids_from_file():
        if chat_id.startswith("-") and chat_id not in FORBIDDEN_CHAT_IDS:
            return chat_id
    return ""


def configured_chat_ids() -> list[str]:
    """Operator + MaximumMint & North. Never the PirateEye realtor group."""
    ids: list[str] = []
    for raw in (
        _default_operator_raw(),
        _default_group_raw(),
        os.environ.get(CHATS_ENV) or "",
    ):
        for chat_id in _parse_chat_ids(raw):
            if chat_id not in ids:
                ids.append(chat_id)
    for chat_id in _chat_ids_from_file():
        if chat_id not in ids:
            ids.append(chat_id)
    return [chat_id for chat_id in ids if chat_id not in FORBIDDEN_CHAT_IDS]


def destination_map() -> dict[str, object]:
    return {
        "agent": "mr-north",
        "bot": "Mr_North_bot",
        "operator_chat_id": operator_chat_id(),
        "group_title": NORTH_GROUP_TITLE,
        "group_chat_id": north_group_chat_id(),
        "chat_ids": configured_chat_ids(),
        "forbidden_chat_ids": sorted(FORBIDDEN_CHAT_IDS),
    }


def configured_chat_id() -> str:
    ids = configured_chat_ids()
    return ids[0] if ids else ""


def save_chat_id(chat_id: str, *, username: str = "") -> Path:
    path = chat_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_chat_file()
    ids = _parse_chat_ids(chat_id)
    if not ids:
        raise TelegramError(
            "Refusing to bind a non-North chat. North reports go to the operator "
            f"and {NORTH_GROUP_TITLE} only."
        )
    for item in _chat_ids_from_file():
        if item not in ids:
            ids.append(item)
    group_id = str(existing.get("group_chat_id") or "")
    if ids[0].startswith("-"):
        group_id = ids[0]
    group_parsed = _parse_chat_ids(group_id)
    group_id = group_parsed[0] if group_parsed else ""
    if group_id and group_id not in ids:
        ids.append(group_id)
    operator = ids[0]
    if operator.startswith("-") and DEFAULT_OPERATOR_CHAT_ID not in ids:
        operator = str(existing.get("chat_id") or operator)
    path.write_text(
        json.dumps(
            {
                "chat_id": operator,
                "group_chat_id": group_id,
                "group_title": NORTH_GROUP_TITLE if group_id else existing.get("group_title") or "",
                "chat_ids": ids,
                "bot": username or existing.get("bot") or "",
                "agent": "mr-north",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def save_group_chat_id(chat_id: str, *, username: str = "") -> Path:
    ids = _parse_chat_ids(chat_id)
    if not ids:
        raise TelegramError(
            f"Refusing to bind a non-North group. Reports go to {NORTH_GROUP_TITLE} only."
        )
    path = chat_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_chat_file()
    group_id = ids[0]
    operator = str(existing.get("chat_id") or operator_chat_id() or "")
    operator_ids = _parse_chat_ids(operator)
    operator = operator_ids[0] if operator_ids else ""
    chat_ids = _parse_chat_ids(
        ",".join(
            [
                operator,
                group_id,
                ",".join(str(item) for item in (existing.get("chat_ids") or [])),
            ]
        )
    )
    path.write_text(
        json.dumps(
            {
                "chat_id": operator or group_id,
                "group_chat_id": group_id,
                "group_title": NORTH_GROUP_TITLE,
                "chat_ids": chat_ids,
                "bot": username or existing.get("bot") or "",
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
                    "and NORTH_TELEGRAM_GROUP_CHAT_ID, or add @Mr_North_bot to "
                    f"{NORTH_GROUP_TITLE} and retry after the other poller stops."
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

    def _try_get_chat(self, chat_id: str) -> dict[str, Any]:
        try:
            result = self._post("getChat", {"chat_id": chat_id}).get("result") or {}
        except TelegramError:
            return {}
        return dict(result) if isinstance(result, dict) else {}

    def group_id_is_wrong_title(self, chat_id: str) -> bool:
        """True when this chat exists but is not MaximumMint & North."""
        chat = self._try_get_chat(str(chat_id or "").strip())
        if not chat:
            return False
        return not is_north_group_chat(chat)

    def discover_north_group(self, *, timeout: int = 0) -> str:
        """One-shot getUpdates. Prefers my_chat_member when the bot was added to the group."""
        data = self._post(
            "getUpdates",
            {
                "timeout": max(0, int(timeout)),
                "limit": 100,
                "allowed_updates": list(GET_UPDATES_ALLOWED),
            },
        )
        return north_group_id_from_updates(data.get("result") or [])

    def resolve_group_chat_id(self, configured: str = "", *, persist: bool = True) -> str:
        """Return the live MaximumMint & North id, discovering it if the default is stale."""
        candidate = str(configured or north_group_chat_id() or "").strip()
        if candidate and candidate not in FORBIDDEN_CHAT_IDS:
            chat = self._try_get_chat(candidate)
            if chat and is_north_group_chat(chat):
                return str(chat["id"])
            if chat and (
                is_forbidden_group_title(str(chat.get("title") or ""))
                or str(chat.get("type") or "") in {"group", "supergroup"}
            ):
                candidate = ""
        discovered = ""
        try:
            discovered = self.discover_north_group(timeout=0)
        except TelegramError:
            discovered = ""
        if discovered:
            if persist:
                try:
                    save_group_chat_id(discovered)
                except TelegramError:
                    pass
            return discovered
        return candidate

    def capture_destinations(self, *, timeout: int = 30) -> dict[str, str]:
        """Bind operator and/or MaximumMint & North from a one-shot getUpdates."""
        data = self._post(
            "getUpdates",
            {
                "timeout": max(0, int(timeout)),
                "limit": 100,
                "allowed_updates": list(GET_UPDATES_ALLOWED),
            },
        )
        operator = ""
        group = ""
        group_title = ""
        for chat in extract_chats_from_updates(data.get("result") or []):
            chat_id = str(chat.get("id") or "").strip()
            if not chat_id or chat_id in FORBIDDEN_CHAT_IDS:
                continue
            if is_forbidden_group_title(str(chat.get("title") or "")):
                continue
            chat_type = str(chat.get("type") or "")
            if chat_type == "private" and not operator:
                operator = chat_id
            if is_north_group_chat(chat):
                group = chat_id
                group_title = str(chat.get("title") or NORTH_GROUP_TITLE)
        if not operator and not group:
            raise TelegramError(
                "No Telegram chat yet. Add @Mr_North_bot to MaximumMint & North "
                "(not MaximumMint & Agent Real), send any message there, or /start "
                "in a private chat, then run telegram-capture again."
            )
        return {
            "operator_chat_id": operator,
            "group_chat_id": group,
            "group_title": group_title,
        }

    def capture_chat_id(self, *, timeout: int = 30) -> str:
        """One-shot getUpdates to bind the chat that messaged North. Not a poller."""
        bound = self.capture_destinations(timeout=timeout)
        chat_id = bound.get("group_chat_id") or bound.get("operator_chat_id") or ""
        if not chat_id:
            raise TelegramError(
                "No Telegram chat yet. Open North's bot, tap Start, then run telegram-capture again."
            )
        return chat_id


def live_client(*, opener: Callable[..., Any] | None = None) -> NorthTelegram:
    token = configured_token()
    if not token:
        raise TelegramError(
            f"No {TOKEN_ENV} configured. Do not use TELEGRAM_BOT_TOKEN (that is @THWellness_bot)."
        )
    return NorthTelegram(token, opener=opener)
