"""Parsed inbound email used by packet intake."""

from __future__ import annotations

import email
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime

KEEP_SUFFIXES = {".csv", ".xlsx", ".xlsm", ".xls", ".pdf", ".txt", ".vcf", ".vcard", ".zip", ".json"}
SKIP_CONTENT_TYPES = {
    "multipart/alternative",
    "multipart/mixed",
    "multipart/related",
    "multipart/signed",
}


@dataclass
class Attachment:
    filename: str
    content_type: str
    data: bytes


@dataclass
class InboundMessage:
    account: str
    uid: str
    message_id: str
    from_header: str
    to_header: str
    cc_header: str
    subject: str
    date: datetime | None
    body_text: str
    attachments: list[Attachment] = field(default_factory=list)
    raw: bytes = b""

    @property
    def addresses_blob(self) -> str:
        return " ".join([self.from_header, self.to_header, self.cc_header, self.subject, self.body_text[:2000]])


def parse_rfc822(raw: bytes, *, account: str, uid: str) -> InboundMessage:
    message = email.message_from_bytes(raw)
    from_header = _decode_header(message.get("From"))
    to_header = _decode_header(message.get("To"))
    cc_header = _decode_header(message.get("Cc"))
    subject = _decode_header(message.get("Subject"))
    message_id = (message.get("Message-ID") or message.get("Message-Id") or "").strip()
    if not message_id:
        digest = hashlib.sha256(raw[:8000] + uid.encode()).hexdigest()[:24]
        message_id = f"<generated-{account}-{uid}-{digest}>"
    body_parts: list[str] = []
    attachments: list[Attachment] = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() in SKIP_CONTENT_TYPES:
                continue
            filename = part.get_filename()
            if filename:
                filename = _decode_header(filename)
                payload = _payload_bytes(part)
                if payload and _keep_attachment(filename, part.get_content_type()):
                    attachments.append(
                        Attachment(filename=filename, content_type=part.get_content_type(), data=payload)
                    )
                continue
            if part.get_content_type() == "text/plain":
                body_parts.append(_payload_text(part))
            elif part.get_content_type() == "text/html" and not body_parts:
                body_parts.append(_html_to_text(_payload_text(part)))
    else:
        if message.get_content_type() == "text/html":
            body_parts.append(_html_to_text(_payload_text(message)))
        else:
            body_parts.append(_payload_text(message))
    return InboundMessage(
        account=account,
        uid=str(uid),
        message_id=message_id,
        from_header=from_header,
        to_header=to_header,
        cc_header=cc_header,
        subject=subject,
        date=_parse_date(message.get("Date")),
        body_text="\n".join(part for part in body_parts if part).strip(),
        attachments=attachments,
        raw=raw,
    )


def _keep_attachment(filename: str, content_type: str) -> bool:
    name = filename.lower()
    if any(name.endswith(suffix) for suffix in KEEP_SUFFIXES):
        return True
    return content_type in {
        "text/csv",
        "application/pdf",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
        "text/vcard",
        "text/x-vcard",
        "application/json",
    }


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out: list[str] = []
    for text, encoding in parts:
        if isinstance(text, bytes):
            out.append(text.decode(encoding or "utf-8", errors="replace"))
        else:
            out.append(text)
    return " ".join(out).strip()


def _payload_bytes(part: Message) -> bytes:
    payload = part.get_payload(decode=True)
    if payload is None:
        return b""
    return payload if isinstance(payload, bytes) else bytes(payload)


def _payload_text(part: Message) -> str:
    data = _payload_bytes(part)
    charset = part.get_content_charset() or "utf-8"
    try:
        return data.decode(charset, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?i)<br\s*/?>", "\n", html)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"(?s)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?s)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+\n", "\n", re.sub(r"[ \t]{2,}", " ", text)).strip()


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
