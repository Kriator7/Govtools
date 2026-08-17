from typing import Any
from uuid import uuid4

from app.integrations.email.base import EmailProvider


class MockEmailProvider(EmailProvider):
    name = "mock"

    def send_email(self, to: str, subject: str, body: str) -> dict[str, Any]:
        return {
            "provider_message_id": f"email-mock-{uuid4().hex[:12]}",
            "to": to,
            "subject": subject,
            "body": body,
            "status": "queued",
        }
