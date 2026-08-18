"""Telegram Bot API abstraction.

Live adapter follows https://core.telegram.org/bots/api — sendMessage,
answerCallbackQuery, getUpdates, deleteWebhook, and webhook secret-token verification.
"""

from abc import ABC, abstractmethod
from typing import Any


class TelegramProvider(ABC):
    name: str = "telegram"

    @abstractmethod
    def send_message(
        self,
        chat_id: str,
        text: str,
        buttons: list | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> tuple[str, str]:
        raise NotImplementedError

    def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> dict[str, Any]:
        return {"ok": True, "callback_query_id": callback_query_id, "text": text}

    def get_updates(self, offset: int | None = None, timeout: int = 0) -> list[dict[str, Any]]:
        return []

    def delete_webhook(self, drop_pending_updates: bool = False) -> dict[str, Any]:
        return {"ok": True, "dropped": drop_pending_updates}
