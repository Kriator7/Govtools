"""Pull labeled packet fields from email bodies, vCards, and simple text attachments."""

from __future__ import annotations

import re
from io import BytesIO

from pypdf import PdfReader

from app.services.inbox.las_vegas_idx import (
    LAS_VEGAS_REALTORS_MLS,
    PACKET_2_FROM_CAT,
    looks_like_las_vegas_realtors_idx,
)
from app.services.inbox.message import Attachment, InboundMessage
from app.services.inbox.redact import redact_text
from app.services.inbox.classify import reply_body
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

NUMBERED_ITEM = re.compile(r"(?ms)^\s*(\d+)\s*[.)]\s*(.*?)(?=^\s*\d+\s*[.)]|\Z)")

PACKET_NUMBER_KEYS = {
    1: {
        1: "name",
        2: "brokerage",
        3: "license_number",
        4: "broker_name",
        5: "office_address",
        6: "phone",
        7: "email",
        8: "timezone",
        9: "side",
    },
    2: {
        1: "mls_name",
        2: "mls_agent_id",
        3: "api_authorization",
        4: "api_vendor",
        5: "vendor_instructions",
        6: "coverage_area",
        7: "listing_statuses",
        8: "store_remarks",
        9: "store_photos",
        10: "check_frequency",
    },
    5: {
        1: "telegram_confirmed",
        2: "telegram_phone",
        3: "telegram_username",
        4: "bot_join_note",
        5: "alert_hours",
        6: "min_score",
        7: "realert_note",
    },
    6: {
        1: "approve_before_text",
        2: "twilio_status",
        3: "outbound_number",
        4: "sample_text",
        5: "reply_words",
        6: "call_instead",
        7: "tcpa",
    },
    7: {
        1: "form_name",
        2: "form_owner",
        3: "may_store",
        4: "may_fill",
        5: "may_send",
        6: "may_esign",
        7: "fillable_pdf",
        8: "platform",
    },
    8: {
        1: "platform",
        2: "broker_requires_platform",
        3: "username",
        4: "integration",
        5: "who_must_sign",
        6: "who_may_send",
        7: "closed_file_notes",
    },
    10: {
        1: "default_earnest",
        2: "inspection_days",
        3: "closing_timeline",
        4: "buyer_name_rule",
        5: "never_alert",
        6: "after_hours",
        7: "escalation_contact",
    },
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
    numbered = numbered_fields(text, packet_number)
    if packet_number == 1:
        fields = labeled_fields(text, PACKET_1_LABELS)
        fields.update(numbered)
        fields.update(_vcard_fields(message.attachments))
        _split_license_expiration(fields)
        if fields.get("phone"):
            fields["phone"] = _normalize_phone(fields["phone"]) or fields["phone"]
        if "timezone" in fields:
            fields["timezone"] = _normalize_timezone(fields["timezone"])
        return fields
    if packet_number == 2:
        fields = labeled_fields(text, PACKET_2_LABELS)
        agent_id = (numbered.get("mls_agent_id") or "").strip()
        if re.fullmatch(r"\d{3,}", agent_id) or not looks_like_las_vegas_realtors_idx(text):
            fields.update(numbered)
        _normalize_mls_name(fields)
        if looks_like_las_vegas_realtors_idx(text) and not fields.get("mls_agent_id"):
            merged = dict(PACKET_2_FROM_CAT)
            merged.update({key: value for key, value in fields.items() if value})
            return merged
        return fields
    if packet_number == 4:
        fields = dict(numbered)
        fields.update(parse_buybox_note(text))
        return fields
    if packet_number == 5:
        fields = labeled_fields(text, PACKET_5_LABELS)
        fields.update(numbered)
        username = fields.get("telegram_username") or _telegram_username(text)
        if username:
            fields["telegram_username"] = username
        _recover_packet5_shift(fields, text)
        if fields.get("telegram_phone"):
            fields["telegram_phone"] = _normalize_phone(fields["telegram_phone"]) or fields["telegram_phone"]
        if "min_score" in fields:
            score = as_int(re.sub(r"[^\d]", "", fields["min_score"]))
            if score:
                fields["min_score"] = str(score)
        if fields.get("realert_note"):
            note = fields["realert_note"].lower()
            fields["realert_price_drop"] = "yes" if "price drop" in note else fields.get("realert_price_drop")
            fields["realert_back_on_market"] = "yes" if "back on market" in note else fields.get("realert_back_on_market")
        blob = reply_body(text).lower()
        if "price drop" in blob:
            fields["realert_price_drop"] = fields.get("realert_price_drop") or "yes"
        if "back on market" in blob:
            fields["realert_back_on_market"] = fields.get("realert_back_on_market") or "yes"
        for flag in ("telegram_confirmed", "realert_price_drop", "realert_back_on_market"):
            if flag in fields:
                parsed = as_bool(fields[flag])
                if parsed is not None:
                    fields[flag] = "yes" if parsed else "no"
        return fields
    if packet_number == 6:
        fields = labeled_fields(text, PACKET_6_LABELS)
        fields.update(numbered)
        return fields
    if packet_number == 8:
        fields = labeled_fields(text, PACKET_8_LABELS)
        fields.update(numbered)
        if "username" in fields and "@" not in fields["username"]:
            if re.fullmatch(r".+\s+\S{8,}", fields["username"]):
                fields["username"] = fields["username"].split()[0]
        return fields
    if packet_number == 10:
        fields = labeled_fields(text, PACKET_10_LABELS)
        fields.update(numbered)
        return fields
    if packet_number in {7, 9}:
        fields = dict(numbered)
        fields["file_count"] = str(len(message.attachments))
        fields["filenames"] = ", ".join(item.filename for item in message.attachments)
        return fields
    return numbered


def numbered_fields(text: str, packet_number: int) -> dict[str, str]:
    keys = PACKET_NUMBER_KEYS.get(packet_number) or {}
    if not keys:
        return {}
    found: dict[str, str] = {}
    for match in NUMBERED_ITEM.finditer(reply_body(text)):
        number = int(match.group(1))
        value = re.sub(r"\s+", " ", match.group(2)).strip().strip(" .;")
        key = keys.get(number)
        if not key or not value:
            continue
        found[key] = value
    return found


def parse_buybox_note(text: str) -> dict[str, str]:
    blob = reply_body(text).lower()
    fields: dict[str, str] = {}
    pct = re.search(r"(\d{2,3})\s*%\s+of\s+(?:market\s+value|arv|market)", blob)
    if pct:
        fields["max_price_pct_of_arv"] = str(round(int(pct.group(1)) / 100, 2))
    if re.search(r"single[\s-]?family", blob):
        fields["property_types"] = "single_family"
    if re.search(r"no\s+hoa", blob):
        fields["hoa_required"] = "false"
    if "subject to change" in blob:
        fields["notes"] = reply_body(text).split("\n")[0].strip()
    return fields


def _combined_text(message: InboundMessage) -> str:
    parts = [message.subject, reply_body(message.body_text)]
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


def _normalize_phone(value: str) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if len(digits) == 10:
        return f"+1{digits}"
    return None


def _split_license_expiration(fields: dict[str, str]) -> None:
    license_number = fields.get("license_number") or ""
    match = re.search(
        r"([BS]\.?\d{5,})(?:\s+exp(?:ires|iration)?\.?:?)?\s+(\d{1,2}/\d{1,2}/\d{2,4})",
        license_number,
        re.I,
    )
    if match:
        fields["license_number"] = match.group(1)
        if "license_expiration" not in fields:
            fields["license_expiration"] = match.group(2)
    broker = fields.get("broker_name") or ""
    broker_match = re.search(r"([BS]\.?\d{5,})", broker, re.I)
    if broker_match and "broker_license" not in fields:
        fields["broker_license"] = broker_match.group(1)
        fields["broker_name"] = re.sub(r"\s+", " ", broker.replace(broker_match.group(1), "")).strip(" -()")


def _normalize_mls_name(fields: dict[str, str]) -> None:
    raw = (fields.get("mls_name") or "").lower().replace(" ", "")
    if "lvrealtor" in raw or "glvar" in raw or "lasvegasrealtor" in raw:
        fields["mls_name"] = LAS_VEGAS_REALTORS_MLS


def _recover_packet5_shift(fields: dict[str, str], text: str) -> None:
    """Damian sometimes skips checklist item 4 (bot-join) and numbers hours as 4."""
    hours_pat = re.compile(r"\d{1,2}\s*(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)", re.I)
    score_pat = re.compile(r"\b([7-9]0)\s*\+")
    join = fields.get("bot_join_note") or ""
    hours = fields.get("alert_hours") or ""
    score = fields.get("min_score") or ""
    if hours_pat.search(join) and (not hours or score_pat.search(hours) or as_int(re.sub(r"[^\d]", "", hours))):
        if not fields.get("realert_note") and score and not score_pat.search(score):
            fields["realert_note"] = score
        if score_pat.search(hours):
            fields["min_score"] = hours
        fields["alert_hours"] = join
    blob = reply_body(text)
    if not fields.get("min_score"):
        found = score_pat.search(blob)
        if found:
            fields["min_score"] = found.group(1)
    if not fields.get("alert_hours"):
        found = re.search(
            r"\d{1,2}\s*(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?).{0,24}\d{1,2}\s*(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)",
            blob,
            re.I,
        )
        if found:
            fields["alert_hours"] = found.group(0)
