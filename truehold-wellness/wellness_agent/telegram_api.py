"""Telegram Bot API client for TrueHold Wellness (@Npeppers_bot) only.

https://core.telegram.org/bots/api
"""

from typing import Any

import httpx

from wellness_agent.identity import assert_wellness_telegram_username

TELEGRAM_ENDPOINT = "https://api.telegram.org"


class WellnessTelegram:
    def __init__(self, bot_token: str) -> None:
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required for live TrueHold Wellness Telegram")
        self.bot_token = bot_token

    def get_username(self) -> str:
        data = self._get("getMe")
        return str((data.get("result") or {}).get("username") or "")

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
