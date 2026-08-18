import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import PROJECT_ROOT
from app.integrations.email.base import EmailProvider


class MockEmailProvider(EmailProvider):
    name = "mock"

    def __init__(self, outbox_path: Path | None = None) -> None:
        self.outbox_path = outbox_path or (PROJECT_ROOT / "data" / "exports" / "email_outbox.json")
        self.sent: list[dict[str, Any]] = []

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
        payload = {
            "provider_message_id": f"email-mock-{uuid4().hex[:12]}",
            "from": from_address,
            "to": to,
            "reply_to": reply_to,
            "intended_recipient": intended_recipient,
            "subject": subject,
            "body": body,
            "status": "delivered",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        self.sent.append(payload)
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
        existing: list[dict[str, Any]] = []
        if self.outbox_path.exists():
            existing = json.loads(self.outbox_path.read_text(encoding="utf-8") or "[]")
        existing.append(payload)
        self.outbox_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        return payload
