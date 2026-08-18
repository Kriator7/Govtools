"""Telegram Bot API client for TrueHold Wellness (@THWellness_bot) only.

https://core.telegram.org/bots/api
"""

from typing import Any

import httpx

from wellness_agent.identity import REQUIRED_USERNAME, assert_wellness_telegram_username
from wellness_agent.telegram_inbound import BOT_COMMANDS

TELEGRAM_ENDPOINT = "https://api.telegram.org"
BOT_DISPLAY_NAME = "TrueHold Wellness"
BOT_DESCRIPTION = (
    "TrueHold Wellness business-inbox agent. Every alert includes a complete "
    "snapshot: orders, payments, fulfillment requests, shipping issues, "
    "cancellations/refunds, peptide messages, and other actionable business email. "
    "Use /inbox, /order, and /start. Not realtor-agent."
)
BOT_SHORT_DESCRIPTION = (
    "TrueHold Wellness inbox: orders, payments, fulfillment, shipping, cancellations, peptides."
)


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

    def send_message(self, chat_id: str, text: str) -> dict[str, Any]:
        data = self._post("sendMessage", {"chat_id": chat_id, "text": text})
        return {"provider_message_id": str((data.get("result") or {}).get("message_id")), "raw": data}

    def get_updates(self, offset: int | None = None, timeout: int = 0) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        data = self._post("getUpdates", payload, timeout=timeout + 10)
        return list(data.get("result") or [])

    def delete_webhook(self) -> dict[str, Any]:
        return self._post("deleteWebhook", {"drop_pending_updates": False})

    def configure_public_profile(self) -> dict[str, Any]:
        """Match the original Wellness bot surface on @THWellness_bot.

        setMyName: https://core.telegram.org/bots/api#setmyname
        setMyDescription: https://core.telegram.org/bots/api#setmydescription
        setMyShortDescription: https://core.telegram.org/bots/api#setmyshortdescription
        setMyCommands: https://core.telegram.org/bots/api#setmycommands
        """
        self.assert_identity()
        name = self._post("setMyName", {"name": BOT_DISPLAY_NAME})
        description = self._post("setMyDescription", {"description": BOT_DESCRIPTION})
        short = self._post("setMyShortDescription", {"short_description": BOT_SHORT_DESCRIPTION})
        commands = self._post("setMyCommands", {"commands": list(BOT_COMMANDS)})
        return {
            "bot": f"@{REQUIRED_USERNAME}",
            "setMyName": name.get("ok"),
            "setMyDescription": description.get("ok"),
            "setMyShortDescription": short.get("ok"),
            "setMyCommands": commands.get("ok"),
        }

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
