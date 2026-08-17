from abc import ABC, abstractmethod
from typing import Any


class EmailProvider(ABC):
    name: str = "email"

    @abstractmethod
    def send_email(self, to: str, subject: str, body: str) -> dict[str, Any]:
        raise NotImplementedError
