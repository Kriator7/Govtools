from abc import ABC, abstractmethod
from typing import Any


class EmailProvider(ABC):
    name: str = "email"

    @abstractmethod
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        *,
        from_address: str,
        reply_to: str | None = None,
        intended_recipient: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError
