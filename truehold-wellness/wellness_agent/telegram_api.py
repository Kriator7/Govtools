"""Telegram Bot API client for TrueHold Wellness (@THWellness_bot) only.

https://core.telegram.org/bots/api
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from wellness_agent.identity import REQUIRED_USERNAME, assert_wellness_telegram_username
from wellness_agent.operator_store import configured_operator_chats
from wellness_agent.telegram_copy import CUSTOMER_COMMANDS, STAFF_COMMANDS

TELEGRAM_ENDPOINT = "https://api.telegram.org"
BOT_DISPLAY_NAME = "TrueHold Wellness"
BOT_DESCRIPTION = (
    "TrueHold Wellness. Say hi to start, then scroll the picture menu and tap the vial you want. "
    "Las Vegas residents only. Educational information only. "
    "Not realtor-agent."
)
BOT_SHORT_DESCRIPTION = "TrueHold Wellness. Say hi to start, then tap the vial you want."


class WellnessTelegram:
    def __init__(self, bot_token: str) -> None:
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required for live TrueHold Wellness Telegram")
        self.bot_token = bot_token

    def get_username(self) -> str:
        data = self._get("getMe")
        return str((data.get("result") or {}).get("username") or "")

    def get_me(self) -> dict[str, Any]:
        return dict((self._get("getMe").get("result") or {}))

    def assert_identity(self) -> str:
        return assert_wellness_telegram_username(self.get_username())

    def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        data = self._post("sendMessage", payload)
        return {"provider_message_id": str((data.get("result") or {}).get("message_id")), "raw": data}

    def send_photo(
        self,
        chat_id: str,
        path: str | Path,
        caption: str = "",
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """sendPhoto: https://core.telegram.org/bots/api#sendphoto"""
        file_path = Path(path)
        payload: dict[str, Any] = {"chat_id": chat_id}
        if caption:
            payload["caption"] = caption[:1024]
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        with file_path.open("rb") as handle, httpx.Client(timeout=60) as client:
            response = client.post(
                self._url("sendPhoto"),
                data=payload,
                files={"photo": (file_path.name, handle, "image/jpeg")},
            )
            response.raise_for_status()
            data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description") or "Telegram sendPhoto failed")
        return {"provider_message_id": str((data.get("result") or {}).get("message_id")), "raw": data}

    def send_document(self, chat_id: str, path: str | Path, caption: str = "") -> dict[str, Any]:
        """sendDocument: https://core.telegram.org/bots/api#senddocument"""
        file_path = Path(path)
        payload = {"chat_id": chat_id}
        if caption:
            payload["caption"] = caption[:1024]
        with file_path.open("rb") as handle, httpx.Client(timeout=60) as client:
            response = client.post(
                self._url("sendDocument"),
                data=payload,
                files={"document": (file_path.name, handle, "application/pdf")},
            )
            response.raise_for_status()
            data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description") or "Telegram sendDocument failed")
        return {"provider_message_id": str((data.get("result") or {}).get("message_id")), "raw": data}

    def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> dict[str, Any]:
        """answerCallbackQuery: https://core.telegram.org/bots/api#answercallbackquery"""
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text[:200]
        return self._post("answerCallbackQuery", payload)

    def get_updates(self, offset: int | None = None, timeout: int = 0) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message", "callback_query"],
        }
        if offset is not None:
            payload["offset"] = offset
        data = self._post("getUpdates", payload, timeout=timeout + 10)
        return list(data.get("result") or [])

    def delete_webhook(self) -> dict[str, Any]:
        return self._post("deleteWebhook", {"drop_pending_updates": False})

    def configure_public_profile(self) -> dict[str, Any]:
        """Customer command menu by default; staff commands only in operator chats.

        setMyName: https://core.telegram.org/bots/api#setmyname
        setMyDescription: https://core.telegram.org/bots/api#setmydescription
        setMyShortDescription: https://core.telegram.org/bots/api#setmyshortdescription
        setMyCommands: https://core.telegram.org/bots/api#setmycommands
        BotCommandScopeChat: https://core.telegram.org/bots/api#botcommandscopechat
        """
        self.assert_identity()
        name = self._configure_call("setMyName", {"name": BOT_DISPLAY_NAME})
        description = self._configure_call("setMyDescription", {"description": BOT_DESCRIPTION})
        short = self._configure_call(
            "setMyShortDescription", {"short_description": BOT_SHORT_DESCRIPTION}
        )
        default = self._configure_call(
            "setMyCommands",
            {"commands": list(CUSTOMER_COMMANDS), "scope": {"type": "default"}},
        )
        private = self._configure_call(
            "setMyCommands",
            {"commands": list(CUSTOMER_COMMANDS), "scope": {"type": "all_private_chats"}},
        )
        staff_scopes: list[str] = []
        for chat_id in configured_operator_chats():
            scope_chat: int | str = int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id
            result = self._configure_call(
                "setMyCommands",
                {
                    "commands": list(STAFF_COMMANDS),
                    "scope": {"type": "chat", "chat_id": scope_chat},
                },
            )
            staff_scopes.append(f"{chat_id}:{result.get('ok')}")
        return {
            "bot": f"@{REQUIRED_USERNAME}",
            "setMyName": name.get("ok"),
            "setMyDescription": description.get("ok"),
            "setMyShortDescription": short.get("ok"),
            "setMyCommandsDefault": default.get("ok"),
            "setMyCommandsPrivate": private.get("ok"),
            "setMyCommandsStaff": staff_scopes,
        }

    def _configure_call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._post(method, payload)
        except httpx.HTTPStatusError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 429:
                return {"ok": False, "description": "429 Too Many Requests"}
            raise

    def _url(self, method: str) -> str:
        return f"{TELEGRAM_ENDPOINT}/bot{self.bot_token}/{method}"

    def _post(self, method: str, payload: dict[str, Any], timeout: int = 20) -> dict[str, Any]:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(self._url(method), json=payload)
            response.raise_for_status()
            data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description") or f"Telegram {method} failed")
        return data

    def _get(self, method: str) -> dict[str, Any]:
        with httpx.Client(timeout=10) as client:
            response = client.get(self._url(method))
            response.raise_for_status()
            data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description") or f"Telegram {method} failed")
        return data
