import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from thw.config import get_settings


class MockWellnessTelegram:
    def __init__(self, outbox_path: Path | None = None) -> None:
        root = get_settings().project_root
        self.outbox_path = outbox_path or (root / "data" / "exports" / "telegram_outbox.json")
        self.sent: list[dict[str, Any]] = []

    def get_username(self) -> str:
        return "Npeppers_bot"

    def assert_identity(self) -> str:
        return "Npeppers_bot"

    def send_message(self, chat_id: str, text: str) -> dict[str, Any]:
        payload = {
            "provider_message_id": f"thw-tg-{uuid4().hex[:10]}",
            "chat_id": chat_id,
            "text": text,
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

    def get_updates(self, offset: int | None = None, timeout: int = 0) -> list[dict[str, Any]]:
        return []

    def delete_webhook(self) -> dict[str, Any]:
        return {"ok": True}
