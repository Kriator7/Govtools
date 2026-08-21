"""Poll Gmail for Damian packet replies and apply them."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.integrations.email.imap_client import ImapAccount, ImapMessageSource, MessageSource
from app.services.inbox.apply import PacketIntakeService
from app.services.inbox.mls_access import (
    apply_mls_credentials,
    extract_mls_credentials,
    format_mls_access_alert,
    is_mls_api_access_mail,
)
from app.services.inbox.status import write_intake_snapshot
from app.services.providers import get_telegram_provider
from app.services.seed import find_damian_realtor


def configured_imap_accounts(settings: Settings) -> list[ImapAccount]:
    accounts: list[ImapAccount] = []
    seen: set[str] = set()
    jrupe7_password = settings.imap_password or settings.jrupe7_imap_password
    watch_user = (settings.imap_username or settings.imap_watch_address or "").strip()
    if watch_user and jrupe7_password:
        accounts.append(
            ImapAccount(
                username=watch_user,
                password=jrupe7_password,
                host=settings.imap_host,
                port=settings.imap_port,
                mailbox=settings.imap_mailbox,
                label=watch_user,
            )
        )
        seen.add(watch_user.lower())
    smtp_user = (settings.email_smtp_username or "").strip()
    smtp_password = settings.email_smtp_password
    if smtp_user and smtp_password and smtp_user.lower() not in seen:
        accounts.append(
            ImapAccount(
                username=smtp_user,
                password=smtp_password,
                host=settings.imap_host,
                port=settings.imap_port,
                mailbox=settings.imap_mailbox,
                label=smtp_user,
            )
        )
    return accounts


class InboxWatchService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        source: MessageSource | None = None,
        telegram=None,
        env_path: Path | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.source = source or ImapMessageSource()
        self.intake = PacketIntakeService(db, self.settings)
        self.telegram = telegram
        self.env_path = env_path

    def poll_once(self) -> dict:
        accounts = configured_imap_accounts(self.settings)
        if not accounts:
            return {
                "ok": False,
                "error": (
                    "No IMAP login available. Add a Gmail App Password for "
                    f"{self.settings.imap_watch_address} as IMAP_PASSWORD / JRUPE7_IMAP_PASSWORD, "
                    "or keep EMAIL_SMTP_USERNAME + EMAIL_SMTP_PASSWORD for the fallback mailbox. "
                    "App passwords: https://support.google.com/accounts/answer/185833"
                ),
                "watch_address": self.settings.imap_watch_address,
                "processed": [],
            }
        seen = _SeenStore(self.settings.inbox_path / "seen.json")
        processed: list[dict] = []
        skipped = 0
        errors: list[dict] = []
        for account in accounts:
            try:
                messages = self.source.fetch(account, lookback_days=self.settings.imap_lookback_days)
            except Exception as exc:  # noqa: BLE001
                errors.append({"account": account.name, "error": str(exc)})
                continue
            for message in messages:
                key = f"{account.name}:{message.message_id}"
                if seen.has(key):
                    skipped += 1
                    continue
                result = self.intake.apply_message(message)
                creds = extract_mls_credentials(message) if result.get("status") != "ignored" else {}
                if creds:
                    applied = apply_mls_credentials(creds, env_path=self.env_path)
                    result["credentials_applied"] = {"ok": applied.get("ok"), "fields": applied.get("fields")}
                    damian = find_damian_realtor(self.db)
                    if damian is not None:
                        damian.mls_config_ref = "secret:mls-trestle-env"
                seen.add(key, result.get("status", "processed"))
                processed.append(result)
                alert = self._maybe_alert_mls_access(message, result)
                if alert:
                    result["mls_access_alert"] = alert
        self.db.commit()
        seen.save()
        snapshot = write_intake_snapshot(self.db, self.settings)
        return {
            "ok": not errors or bool(processed),
            "watch_address": self.settings.imap_watch_address,
            "accounts": [account.name for account in accounts],
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
            "snapshot": str(snapshot) if snapshot else None,
            "waiting_for": "MLS API access reply (Trestle Technology Provider / Las Vegas REALTORS MLO)",
        }

    def _maybe_alert_mls_access(self, message, result: dict) -> dict | None:
        if result.get("status") in {"ignored"}:
            return None
        if not result.get("credentials_applied") and not is_mls_api_access_mail(message):
            return None
        text = format_mls_access_alert(message, result)
        chat_id = self.settings.telegram_operator_chat_id
        payload = {"text": text, "chat_id": chat_id, "sent": False}
        if self.settings.telegram_mode == "live" and chat_id and chat_id != "mock-realtor":
            telegram = self.telegram or get_telegram_provider(self.settings)
            sent = telegram.send_message(str(chat_id), text)
            payload["sent"] = True
            payload["provider_message_id"] = sent.get("provider_message_id")
        elif self.telegram is not None and chat_id:
            sent = self.telegram.send_message(str(chat_id), text)
            payload["sent"] = True
            payload["provider_message_id"] = sent.get("provider_message_id")
        return payload


def poll_forever(db: Session, *, once: bool = False, source: MessageSource | None = None) -> int:
    settings = get_settings()
    watcher = InboxWatchService(db, settings, source=source)
    while True:
        result = watcher.poll_once()
        print(json.dumps(_jsonable(result), default=str), flush=True)
        if once:
            return 0 if result.get("ok") or not result.get("errors") else 1
        time.sleep(max(15, int(settings.imap_poll_seconds)))


class _SeenStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, dict] = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data = loaded
            except json.JSONDecodeError:
                self.data = {}

    def has(self, key: str) -> bool:
        return key in self.data

    def add(self, key: str, status: str) -> None:
        self.data[key] = {"status": status, "at": datetime.now(timezone.utc).isoformat()}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
