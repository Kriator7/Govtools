import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import PROJECT_ROOT
from app.integrations.twilio.base import SMSProvider


class MockSMSProvider(SMSProvider):
    name = "mock"

    def __init__(self, outbox_path: Path | None = None) -> None:
        self.outbox_path = outbox_path or (PROJECT_ROOT / "data" / "exports" / "sms_outbox.json")
        self.sent: list[dict[str, Any]] = []

    def send_sms(self, to: str, body: str) -> dict[str, Any]:
        payload = {
            "provider_message_id": f"sms-mock-{uuid4().hex[:12]}",
            "to": to,
            "body": body,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "delivered",
        }
        self.sent.append(payload)
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
        existing: list[dict[str, Any]] = []
        if self.outbox_path.exists():
            existing = json.loads(self.outbox_path.read_text(encoding="utf-8") or "[]")
        existing.append(payload)
        self.outbox_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        return payload

    def health(self) -> tuple[str, str]:
        return ("ok", "mock sms provider")
