"""Apply Damian packet replies to realtor, investors, and stored packet rows."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.enums import ActorOrigin, ActorType, PacketStatus
from app.models.realtor import Realtor
from app.models.realtor_packet import RealtorPacket
from app.services.audit import AuditService
from app.services.importing import InvestorImportService
from app.services.inbox.classify import classify_packets, is_packet_candidate
from app.services.inbox.message import Attachment, InboundMessage
from app.services.inbox.parse import extract_packet_fields
from app.services.inbox.redact import looks_like_secret_filename, redact_text
from app.services.seed import upsert_damian_realtor
from app.utilities.ids import next_public_id
from app.utilities.parsing import as_bool, as_int


TABULAR_SUFFIXES = {".csv", ".xlsx", ".xlsm", ".xls"}


class PacketIntakeService:
    def __init__(self, db: Session, settings: Settings | None = None, audit: AuditService | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.audit = audit or AuditService(db)
        self._import_cache: dict[str, dict] = {}

    def apply_message(self, message: InboundMessage) -> dict:
        extra_from = [
            row.email
            for row in self.db.query(Realtor).filter(Realtor.email.isnot(None)).all()
            if row.email and "einbinder" in (row.name or "").lower()
        ]
        if not is_packet_candidate(message, self.settings.imap_watch_address, extra_from=extra_from):
            return {"status": PacketStatus.IGNORED.value, "message_id": message.message_id, "reason": "not a Damian packet reply"}
        packets = classify_packets(message)
        saved_files = self._store_raw(message)
        realtor = upsert_damian_realtor(self.db)
        if not packets:
            row = self._upsert_row(realtor, message, 0, saved_files, {}, PacketStatus.UNCLASSIFIED.value)
            row.notes = redact_text(message.body_text)[:4000]
            self.db.flush()
            return {
                "status": PacketStatus.UNCLASSIFIED.value,
                "message_id": message.message_id,
                "realtor_id": realtor.public_id,
                "packets": [0],
                "saved_files": saved_files,
            }
        results = []
        for number in packets:
            result = self._apply_packet(realtor, message, number, saved_files)
            results.append(result)
        return {
            "status": PacketStatus.APPLIED.value
            if all(item["status"] == PacketStatus.APPLIED.value for item in results)
            else PacketStatus.PARTIAL.value,
            "message_id": message.message_id,
            "realtor_id": realtor.public_id,
            "packets": results,
            "saved_files": saved_files,
        }

    def _apply_packet(self, realtor: Realtor, message: InboundMessage, number: int, saved_files: list[str]) -> dict:
        fields = extract_packet_fields(message, number)
        apply_result: dict = {"packet": number}
        if number == 1:
            realtor = upsert_damian_realtor(self.db, fields)
            apply_result["realtor"] = {
                "public_id": realtor.public_id,
                "name": realtor.name,
                "brokerage": realtor.brokerage,
                "email": realtor.email,
            }
        elif number in {3, 4}:
            apply_result["import"] = self._import_tabular(realtor, message)
        elif number == 5:
            apply_result["notification_settings"] = self._apply_alerts(realtor, fields)
        elif number == 2:
            apply_result["mls"] = self._apply_mls_notes(realtor, fields)
        elif number in {6, 7, 8, 9, 10}:
            apply_result["stored"] = True
            self._append_notes(realtor, number, fields, message)
        missing = _missing_for_packet(number, fields, apply_result)
        status = PacketStatus.APPLIED.value if not missing else PacketStatus.PARTIAL.value
        row = self._upsert_row(realtor, message, number, saved_files, fields, status)
        row.missing_fields = missing
        row.apply_result = apply_result
        row.notes = redact_text(message.body_text)[:4000] or None
        self.db.flush()
        self.audit.record(
            event="PACKET_APPLIED",
            object_type="realtor_packet",
            object_id=row.public_id,
            actor="inbox_watch",
            actor_type=ActorType.SYSTEM.value,
            origin=ActorOrigin.AUTOMATION.value,
            realtor_id=str(realtor.id),
            after_state={"packet": number, "status": status, "missing": missing},
        )
        return {"packet": number, "status": status, "missing": missing, "result": apply_result}

    def _import_tabular(self, realtor: Realtor, message: InboundMessage) -> dict:
        cached = self._import_cache.get(message.message_id)
        if cached is not None:
            return cached
        importer = InvestorImportService(self.db, audit=self.audit)
        combined = {"created_investors": 0, "created_profiles": 0, "errors": [], "files": []}
        for item in _tabular_attachments(message.attachments):
            imported = importer.import_bytes(realtor, item.data, item.filename)
            combined["created_investors"] += imported["created_investors"]
            combined["created_profiles"] += imported["created_profiles"]
            combined["errors"].extend(imported["errors"])
            combined["files"].append(item.filename)
        self._import_cache[message.message_id] = combined
        return combined

    def _apply_alerts(self, realtor: Realtor, fields: dict[str, str]) -> dict:
        settings = dict(realtor.notification_settings or {})
        if fields.get("telegram_confirmed"):
            settings["telegram"] = as_bool(fields["telegram_confirmed"]) is not False
        if fields.get("telegram_username"):
            settings["telegram_username"] = fields["telegram_username"]
        if fields.get("telegram_phone") and not realtor.phone:
            realtor.phone = fields["telegram_phone"]
        if fields.get("alert_hours"):
            settings["alert_hours"] = fields["alert_hours"]
        if fields.get("min_score"):
            score = as_int(fields["min_score"])
            if score:
                settings["alert_min_score"] = score
        if fields.get("realert_price_drop"):
            settings["realert_price_drop"] = as_bool(fields["realert_price_drop"]) is True
        if fields.get("realert_back_on_market"):
            settings["realert_back_on_market"] = as_bool(fields["realert_back_on_market"]) is True
        realtor.notification_settings = settings
        if fields.get("telegram_username") and not realtor.telegram_user_id:
            realtor.telegram_user_id = fields["telegram_username"]
        self.db.flush()
        return settings

    def _apply_mls_notes(self, realtor: Realtor, fields: dict[str, str]) -> dict:
        safe = {key: value for key, value in fields.items() if "password" not in key.lower()}
        if safe.get("mls_name") and not realtor.mls_config_ref:
            realtor.mls_config_ref = "secret:mls-live-config"
        note = "Packet 2 MLS metadata (no passwords stored): " + json.dumps(safe, sort_keys=True)
        self._append_notes(realtor, 2, safe, None, extra=note)
        return safe

    def _append_notes(
        self,
        realtor: Realtor,
        number: int,
        fields: dict,
        message: InboundMessage | None,
        extra: str | None = None,
    ) -> None:
        chunks = [realtor.notes or "", f"Packet {number} received."]
        if extra:
            chunks.append(extra)
        if fields:
            chunks.append(json.dumps(fields, sort_keys=True))
        if message and message.attachments:
            chunks.append("Files: " + ", ".join(item.filename for item in message.attachments))
        realtor.notes = redact_text("\n".join(chunk for chunk in chunks if chunk))[:8000]
        self.db.flush()

    def _store_raw(self, message: InboundMessage) -> list[str]:
        root = self.settings.inbox_path
        safe_id = "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in message.message_id)[:80]
        folder = root / message.account.replace("@", "_at_") / safe_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "message.eml").write_bytes(message.raw or message.body_text.encode("utf-8"))
        meta = {
            "message_id": message.message_id,
            "account": message.account,
            "uid": message.uid,
            "from": message.from_header,
            "to": message.to_header,
            "subject": message.subject,
            "date": message.date.isoformat() if message.date else None,
        }
        (folder / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        (folder / "body.txt").write_text(redact_text(message.body_text), encoding="utf-8")
        saved = [str(folder / "message.eml")]
        for item in _expand_attachments(message.attachments):
            if looks_like_secret_filename(item.filename):
                continue
            path = folder / Path(item.filename).name
            path.write_bytes(item.data)
            saved.append(str(path))
        return saved

    def _upsert_row(
        self,
        realtor: Realtor,
        message: InboundMessage,
        number: int,
        saved_files: list[str],
        fields: dict,
        status: str,
    ) -> RealtorPacket:
        row = (
            self.db.query(RealtorPacket)
            .filter(RealtorPacket.message_id == message.message_id, RealtorPacket.packet_number == number)
            .one_or_none()
        )
        if row is None:
            row = RealtorPacket(
                public_id=next_public_id(self.db, "PKT"),
                realtor_id=realtor.id,
                packet_number=number,
                message_id=message.message_id,
            )
            self.db.add(row)
        row.realtor_id = realtor.id
        row.status = status
        row.account = message.account
        row.from_header = message.from_header[:500]
        row.to_header = message.to_header
        row.subject = (message.subject or "")[:500]
        row.received_at = message.date
        row.payload = fields
        row.attachments = [Path(path).name for path in saved_files]
        row.raw_path = saved_files[0] if saved_files else None
        self.db.flush()
        return row


def _tabular_attachments(attachments: list[Attachment]) -> list[Attachment]:
    found: list[Attachment] = []
    for item in _expand_attachments(attachments):
        suffix = Path(item.filename).suffix.lower()
        if suffix in TABULAR_SUFFIXES:
            found.append(item)
    return found


def _expand_attachments(attachments: list[Attachment]) -> list[Attachment]:
    expanded: list[Attachment] = []
    for item in attachments:
        suffix = Path(item.filename).suffix.lower()
        if suffix != ".zip":
            expanded.append(item)
            continue
        try:
            with zipfile.ZipFile(BytesIO(item.data)) as archive:
                for info in archive.infolist():
                    if info.is_dir() or ".." in Path(info.filename).parts:
                        continue
                    name = Path(info.filename).name
                    if Path(name).suffix.lower() not in TABULAR_SUFFIXES | {".pdf", ".txt", ".vcf", ".vcard", ".json"}:
                        continue
                    expanded.append(
                        Attachment(filename=name, content_type="application/octet-stream", data=archive.read(info))
                    )
        except zipfile.BadZipFile:
            continue
    return expanded


def _missing_for_packet(number: int, fields: dict, apply_result: dict) -> list[str]:
    if number == 1:
        required = ["name", "brokerage", "license_number", "phone", "email"]
        return [key for key in required if not fields.get(key)]
    if number in {3, 4}:
        imported = apply_result.get("import") or {}
        if imported.get("created_investors") or imported.get("created_profiles"):
            return []
        return ["investor spreadsheet"]
    if number == 5:
        required = ["telegram_username", "alert_hours", "min_score"]
        return [key for key in required if not fields.get(key)]
    return []
