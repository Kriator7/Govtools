"""Live Telegram Bot API client. Token must come from Secret Manager / env.

https://core.telegram.org/bots/api
"""

from typing import Any

import httpx

from app.integrations.telegram.base import TelegramProvider

TELEGRAM_ENDPOINT = "https://api.telegram.org"


def _inline_keyboard(buttons: list | None) -> dict[str, Any] | None:
    if not buttons:
        return None
    rows = buttons if buttons and isinstance(buttons[0], list) else [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    keyboard = []
    for row in rows:
        keyboard.append([_telegram_button(button) for button in row])
    return {"inline_keyboard": keyboard}


def _telegram_button(button: dict[str, str]) -> dict[str, str]:
    payload = {"text": button["text"]}
    if button.get("url"):
        payload["url"] = button["url"]
    else:
        payload["callback_data"] = button["callback_data"]
    return payload


class LiveTelegramProvider(TelegramProvider):
    name = "live"

    def __init__(self, bot_token: str) -> None:
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required for live mode")
        self.bot_token = bot_token

    def send_message(
        self,
        chat_id: str,
        text: str,
        buttons: list | None = None,
    ) -> dict[str, Any]:
        # sendMessage: https://core.telegram.org/bots/api#sendmessage
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        markup = _inline_keyboard(buttons)
        if markup:
            payload["reply_markup"] = markup
        data = self._post("sendMessage", payload)
        return {
            "provider_message_id": str(data.get("result", {}).get("message_id")),
            "raw": data,
        }

    def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> dict[str, Any]:
        # answerCallbackQuery: https://core.telegram.org/bots/api#answercallbackquery
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        return self._post("answerCallbackQuery", payload)

    def get_updates(self, offset: int | None = None, timeout: int = 0) -> list[dict[str, Any]]:
        # getUpdates: https://core.telegram.org/bots/api#getupdates
        payload: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        data = self._post("getUpdates", payload, timeout=timeout + 10)
        return list(data.get("result") or [])

    def delete_webhook(self, drop_pending_updates: bool = False) -> dict[str, Any]:
        # deleteWebhook: https://core.telegram.org/bots/api#deletewebhook
        return self._post(
            "deleteWebhook",
            {"drop_pending_updates": drop_pending_updates},
        )

    def health(self) -> tuple[str, str]:
        # getMe: https://core.telegram.org/bots/api#getme
        try:
            data = self._get("getMe")
            username = (data.get("result") or {}).get("username")
            return ("ok", f"telegram getMe succeeded (@{username})" if username else "telegram getMe succeeded")
        except Exception as exc:  # noqa: BLE001
            return ("error", str(exc))

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
