"""Telegram Bot API abstraction.

Live adapter should follow https://core.telegram.org/bots/api — sendMessage,
answerCallbackQuery, and webhook secret-token verification.
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
        buttons: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> tuple[str, str]:
        raise NotImplementedError
