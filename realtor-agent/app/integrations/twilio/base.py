"""SMS provider interface. Live Twilio Messages API: https://www.twilio.com/docs/sms"""

from abc import ABC, abstractmethod
from typing import Any


class SMSProvider(ABC):
    name: str = "sms"

    @abstractmethod
    def send_sms(self, to: str, body: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> tuple[str, str]:
        raise NotImplementedError
