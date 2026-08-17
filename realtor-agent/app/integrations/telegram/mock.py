"""Writes realtor alerts to a local outbox so the demo needs no bot token."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import PROJECT_ROOT
from app.integrations.telegram.base import TelegramProvider


class MockTelegramProvider(TelegramProvider):
    name = "mock"

    def __init__(self, outbox_path: Path | None = None) -> None:
        self.outbox_path = outbox_path or (PROJECT_ROOT / "data" / "exports" / "telegram_outbox.json")
        self.sent: list[dict[str, Any]] = []

    def send_message(
        self,
        chat_id: str,
        text: str,
        buttons: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "provider_message_id": f"tg-mock-{uuid4().hex[:12]}",
            "chat_id": chat_id,
            "text": text,
            "buttons": buttons or [],
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

    def health(self) -> tuple[str, str]:
        return ("ok", "mock telegram provider")
