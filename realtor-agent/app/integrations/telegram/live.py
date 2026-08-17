"""Live Telegram Bot API client. Token must come from Secret Manager / env."""

from typing import Any

import httpx

from app.integrations.telegram.base import TelegramProvider

TELEGRAM_API = "https://api.telegram.org"


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
        buttons: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        # sendMessage: https://core.telegram.org/bots/api#sendmessage
        reply_markup = None
        if buttons:
            reply_markup = {
                "inline_keyboard": [
                    [{"text": button["text"], "callback_data": button["callback_data"]}]
                    for button in buttons
                ]
            }
        with httpx.Client(timeout=20) as client:
            response = client.post(
                f"{TELEGRAM_API}/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "reply_markup": reply_markup,
                },
            )
            response.raise_for_status()
            data = response.json()
        return {
            "provider_message_id": str(data.get("result", {}).get("message_id")),
            "raw": data,
        }

    def health(self) -> tuple[str, str]:
        # getMe: https://core.telegram.org/bots/api#getme
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(f"{TELEGRAM_API}/bot{self.bot_token}/getMe")
                response.raise_for_status()
            return ("ok", "telegram getMe succeeded")
        except Exception as exc:  # noqa: BLE001
            return ("error", str(exc))
