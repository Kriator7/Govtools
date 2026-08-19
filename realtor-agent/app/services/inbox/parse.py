"""Pull labeled packet fields from email bodies, vCards, and simple text attachments."""

from __future__ import annotations

import re
from io import BytesIO

from pypdf import PdfReader

from app.services.inbox.las_vegas_idx import PACKET_2_FROM_CAT, looks_like_las_vegas_realtors_idx
from app.services.inbox.message import Attachment, InboundMessage
from app.services.inbox.redact import redact_text
from app.utilities.parsing import as_bool, as_int

PACKET_1_LABELS = {
    "name": ("full legal name", "legal name", "name as it appears", "name"),
    "brokerage": ("brokerage legal name", "brokerage", "dba"),
    "license_number": ("nevada license number", "license number", "license"),
    "license_expiration": ("license expiration", "expiration date"),
    "broker_name": ("designated broker", "broker name"),
    "broker_license": ("broker license",),
    "office_address": ("office address", "address"),
    "phone": ("mobile phone", "mobile", "cell", "phone"),
    "email": ("work email", "email"),
    "timezone": ("timezone", "time zone"),
    "side": ("listing-side", "buyer-side", "both", "side"),
}

PACKET_2_LABELS = {
    "mls_name": ("mls name", "mls"),
    "mls_agent_id": ("mls agent id", "agent id"),
    "api_vendor": ("vendor name", "feed vendor", "bridge", "spark", "reso"),
    "coverage_area": ("coverage area", "counties", "cities"),
    "listing_statuses": ("listing statuses", "statuses to watch"),
    "store_remarks": ("store listing remarks", "agent remarks"),
    "store_photos": ("store listing photos", "photos"),
    "check_frequency": ("how often", "check frequency"),
}

PACKET_5_LABELS = {
    "telegram_confirmed": ("telegram as the command center", "will use telegram"),
    "telegram_phone": ("mobile number that will install telegram", "telegram phone"),
    "telegram_username": ("telegram username", "username"),
    "alert_hours": ("hours we may alert", "alert hours", "hours"),
    "min_score": ("minimum match score", "min score", "alert score"),
    "realert_price_drop": ("re-alert on price drops", "price drops"),
    "realert_back_on_market": ("back on market",),
}

PACKET_6_LABELS = {
    "approve_before_text": ("only after you tap approve", "written ok"),
    "twilio_status": ("twilio account", "i do not have twilio"),
    "outbound_number": ("outbound phone", "from number"),
    "sample_text": ("sample text",),
    "reply_words": ("reply words", "yes / no / more info"),
    "call_instead": ("must be called",),
    "tcpa": ("tcpa", "agreed to receive"),
}

PACKET_8_LABELS = {
    "platform": ("platform name", "dotloop", "skyslope", "qualia", "docusign"),
    "broker_requires_platform": ("broker requires",),
    "username": ("login username", "username"),
    "who_must_sign": ("who must sign",),
    "who_may_send": ("who is allowed to press send", "press send"),
}

PACKET_10_LABELS = {
    "default_earnest": ("default earnest", "earnest money"),
    "inspection_days": ("inspection", "due-diligence days", "due diligence"),
    "closing_timeline": ("default closing", "closing timeline"),
    "buyer_name_rule": ("buyer name", "entity vs person"),
    "never_alert": ("never want alerted", "exclude"),
    "after_hours": ("after-hours", "after hours"),
    "escalation_contact": ("system is down", "who we contact"),
}


def labeled_fields(text: str, labels: dict[str, tuple[str, ...]]) -> dict[str, str]:
    cleaned = redact_text(text)
    found: dict[str, str] = {}
    for key, names in labels.items():
        for name in names:
            match = re.search(
                rf"(?im)^[ \t]*{re.escape(name)}[ \t]*[:\-–][ \t]*(.+)$",
                cleaned,
            )
            if match:
                value = match.group(1).strip().strip(" .;")
                if value and value.lower() not in {"n/a", "na", "none"}:
                    found[key] = value
                    break
    return found


def extract_packet_fields(message: InboundMessage, packet_number: int) -> dict:
    text = _combined_text(message)
    if packet_number == 1:
        fields = labeled_fields(text, PACKET_1_LABELS)
        fields.update(_vcard_fields(message.attachments))
        if "timezone" in fields:
            fields["timezone"] = _normalize_timezone(fields["timezone"])
        return fields
    if packet_number == 2:
        fields = labeled_fields(text, PACKET_2_LABELS)
        if looks_like_las_vegas_realtors_idx(text):
            merged = dict(PACKET_2_FROM_CAT)
            merged.update({key: value for key, value in fields.items() if value})
            return merged
        return fields
    if packet_number == 5:
        fields = labeled_fields(text, PACKET_5_LABELS)
        username = fields.get("telegram_username") or _telegram_username(text)
        if username:
            fields["telegram_username"] = username
        if "min_score" in fields:
            score = as_int(re.sub(r"[^\d]", "", fields["min_score"]))
            if score:
                fields["min_score"] = str(score)
        for flag in ("telegram_confirmed", "realert_price_drop", "realert_back_on_market"):
            if flag in fields:
                parsed = as_bool(fields[flag])
                if parsed is not None:
                    fields[flag] = "yes" if parsed else "no"
        return fields
    if packet_number == 6:
        return labeled_fields(text, PACKET_6_LABELS)
    if packet_number == 8:
        fields = labeled_fields(text, PACKET_8_LABELS)
        if "username" in fields and "@" not in fields["username"]:
            # login username only — never keep a password-shaped value
            if re.fullmatch(r".+\s+\S{8,}", fields["username"]):
                fields["username"] = fields["username"].split()[0]
        return fields
    if packet_number == 10:
        return labeled_fields(text, PACKET_10_LABELS)
    if packet_number in {7, 9}:
        return {
            "file_count": str(len(message.attachments)),
            "filenames": ", ".join(item.filename for item in message.attachments),
        }
    return {}


def _combined_text(message: InboundMessage) -> str:
    parts = [message.subject, message.body_text]
    for item in message.attachments:
        name = item.filename.lower()
        if name.endswith((".txt", ".vcf", ".vcard", ".json")):
            parts.append(item.data.decode("utf-8", errors="replace"))
        elif name.endswith(".pdf"):
            parts.append(_pdf_text(item))
    return redact_text("\n".join(parts))


def _pdf_text(item: Attachment) -> str:
    try:
        reader = PdfReader(BytesIO(item.data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:  # noqa: BLE001
        return ""


def _vcard_fields(attachments: list[Attachment]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in attachments:
        if not item.filename.lower().endswith((".vcf", ".vcard")):
            continue
        text = item.data.decode("utf-8", errors="replace")
        fn = re.search(r"(?im)^FN:(.+)$", text)
        org = re.search(r"(?im)^ORG:(.+)$", text)
        tel = re.search(r"(?im)^TEL[^:]*:(.+)$", text)
        email_match = re.search(r"(?im)^EMAIL[^:]*:(.+)$", text)
        if fn and "name" not in fields:
            fields["name"] = fn.group(1).strip()
        if org and "brokerage" not in fields:
            fields["brokerage"] = org.group(1).strip()
        if tel and "phone" not in fields:
            fields["phone"] = tel.group(1).strip()
        if email_match and "email" not in fields:
            fields["email"] = email_match.group(1).strip()
    return fields


def _telegram_username(text: str) -> str | None:
    match = re.search(r"(?<!\w)@([A-Za-z0-9_]{5,32})\b", text)
    if match:
        return f"@{match.group(1)}"
    return None


def _normalize_timezone(value: str) -> str:
    lowered = value.lower()
    if "pacific" in lowered or "las vegas" in lowered or "nevada" in lowered:
        return "America/Los_Angeles"
    return value
