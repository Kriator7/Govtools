"""Ask Damian for Packet 2 IDX choice over Telegram and apply his reply.

Do not scrape Matrix. Do not sign up for Trestle here. Do not SMS Damian.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.enums import PacketStatus
from app.models.realtor import Realtor
from app.models.realtor_packet import RealtorPacket
from app.services.inbox.apply import PacketIntakeService, _missing_for_packet
from app.services.inbox.las_vegas_idx import IDX_OPTIONS, PACKET_2_FROM_CAT, TRESTLE_SIGNUP_URL
from app.services.inbox.status import write_intake_snapshot
from app.services.seed import DAMIAN_NAME, find_damian_realtor, upsert_damian_realtor
from app.utilities.ids import next_public_id

IDX_ASK_TEXT = (
    "@damianlasvegas Packet 2 — live MLS for Agent Real.\n"
    "\n"
    "To pull listings I need the authorized API. I cannot use a website plugin "
    "and I will not scrape Matrix.\n"
    "\n"
    "Please reply here with:\n"
    "1. IDX option 3 (Trestle WebAPI) — yes or no.\n"
    "   Option 1 is a Matrix frame (website only). Option 2 is an IDX plugin "
    "(website only). Cat: do not choose 2 and 3 together.\n"
    "2. Your MLS agent ID (numbers only).\n"
    "3. Confirm coverage: Las Vegas, North Las Vegas, Henderson — Active listings.\n"
    "\n"
    "Example:\n"
    "Option 3 yes\n"
    "MLS agent ID: 123456\n"
    "Coverage: LV / NLV / Henderson, Active only\n"
    "\n"
    "I will record the answer. Relays stay on. I will not text Amos or investors."
)

IDX_SMS_TEXT = (
    "Damian — Agent Real needs live MLS. Please reply in the Telegram group "
    "(or here) with: (1) IDX option 3 yes — Trestle WebAPI, not the website "
    "plugin and not a Matrix scrape; (2) your MLS agent ID; (3) confirm "
    "Las Vegas / North Las Vegas / Henderson, Active listings. "
    "Do not pick option 2 and 3 together."
)

OPTION_3_RE = re.compile(
    r"\boption\s*3\b|\bidx\s*3\b|\btrestle\b|\bweb\s*api\b|\bwebapi\b|"
    r"\bchoose\s*3\b|\bgo\s+with\s*3\b|\buse\s*3\b",
    re.I,
)
OPTION_2_RE = re.compile(r"\boption\s*2\b|\bidx\s*plugin\b|\bwordpress\b|\bihomefinder\b", re.I)
OPTION_1_RE = re.compile(r"\boption\s*1\b|\bframe\s*link\b|\bmatrix\s+frame\b", re.I)
YES_RE = re.compile(r"\byes\b|\bapproved\b|\bconfirm(?:ed)?\b|\bok\b|\bgo\s+ahead\b", re.I)
NO_RE = re.compile(r"\bno\b|\bnot\s+yet\b|\bdon'?t\b|\bdo not\b", re.I)
AGENT_ID_RE = re.compile(
    r"(?:mls\s*)?(?:agent|member)\s*id(?:\s+is)?\s*[:#]?\s*(\d{4,})|"
    r"\bid(?:\s+is)?\s*[:#]\s*(\d{4,})",
    re.I,
)
ASK_CONTEXT_RE = re.compile(r"packet\s*2|trestle|webapi|idx option|mls agent id", re.I)
IDX_FIELD_KEYS = (
    "mls_name",
    "idx_contact_name",
    "idx_contact_role",
    "idx_contact_org",
    "idx_option_1",
    "idx_option_2",
    "idx_option_3",
    "idx_rule",
    "chosen_idx_option",
    "agent_usable_option",
    "trestle_signup_url",
    "api_vendor",
    "mls_agent_id",
    "coverage_area",
    "listing_statuses",
    "telegram_idx_reply",
)
CONTRACT_NOISE_RE = re.compile(
    r"escrow|purchase agreement|title insurance|earnest money|close of escrow|"
    r"fixtures and personal property|due diligence|transfer of title|1099",
    re.I,
)


def parse_idx_reply(text: str, *, reply_to: str | None = None) -> dict:
    raw = str(text or "").strip()
    reply_to = str(reply_to or "")
    in_ask_thread = bool(ASK_CONTEXT_RE.search(reply_to))
    chosen = None
    if OPTION_3_RE.search(raw):
        chosen = "3"
    elif OPTION_2_RE.search(raw):
        chosen = "2"
    elif OPTION_1_RE.search(raw):
        chosen = "1"
    elif in_ask_thread and YES_RE.search(raw) and not NO_RE.search(raw):
        chosen = "3"
    agent_id = None
    match = AGENT_ID_RE.search(raw)
    if match:
        agent_id = match.group(1) or match.group(2)
    coverage = None
    if re.search(r"henderson|north las vegas|\blv\b|las vegas", raw, re.I):
        coverage = "Las Vegas; North Las Vegas; Henderson"
    statuses = None
    if re.search(r"\bactive\b", raw, re.I):
        statuses = "active"
    parsed = {
        "raw": raw,
        "chosen_idx_option": chosen,
        "mls_agent_id": agent_id,
        "coverage_area": coverage,
        "listing_statuses": statuses,
        "in_ask_thread": in_ask_thread,
    }
    parsed["has_idx"] = any(
        [parsed["chosen_idx_option"], parsed["mls_agent_id"], parsed["coverage_area"], parsed["listing_statuses"]]
    )
    return parsed


def apply_idx_reply(
    db: Session,
    *,
    text: str,
    reply_to: str | None = None,
    from_user: dict | None = None,
) -> dict:
    parsed = parse_idx_reply(text, reply_to=reply_to)
    if not parsed.get("has_idx"):
        return {"ok": False, "applied": False, "parsed": parsed}
    damian = find_damian_realtor(db) or upsert_damian_realtor(db, {"name": DAMIAN_NAME})
    fields = _sanitize_idx_fields(_merge_packet2_fields(db, damian, parsed))
    intake = PacketIntakeService(db)
    apply_result = {"packet": 2, "mls": intake._apply_mls_notes(damian, fields)}
    missing = _missing_for_packet(2, fields, apply_result)
    if fields.get("chosen_idx_option") and fields.get("chosen_idx_option") != "3":
        missing = list(missing) + ["usable_idx_option_3"]
    row = _upsert_telegram_packet2(db, damian, fields, missing, apply_result, from_user)
    write_intake_snapshot(db)
    return {
        "ok": True,
        "applied": True,
        "parsed": parsed,
        "packet_id": row.public_id,
        "missing_fields": missing,
        "mls_config_ref": damian.mls_config_ref,
        "feeds_this_agent": fields.get("chosen_idx_option") == "3",
        "reply": format_idx_confirmation(parsed, missing, fields),
    }


def format_idx_confirmation(parsed: dict, missing: list[str], fields: dict | None = None) -> str:
    fields = fields or {}
    chosen = parsed.get("chosen_idx_option") or fields.get("chosen_idx_option")
    lines = ["Got it. Packet 2 updated from Telegram."]
    if parsed.get("chosen_idx_option") == "3":
        lines.insert(0, "Thank you, Damian. Option 3 is recorded.")
    if chosen == "3":
        lines.append(
            f"IDX choice: option 3 — {IDX_OPTIONS['3']['name']}. "
            "That is the authorized MLS API for this agent (not a Matrix login and not a website plugin)."
        )
        lines.append(f"Signup path (not done yet): {TRESTLE_SIGNUP_URL}")
        lines.append("Live MLS stays disconnected until Trestle credentials exist. I will not scrape Matrix.")
    elif chosen == "2":
        lines.append(
            "IDX choice: option 2 — website plugin. That does not feed this agent. "
            "Cat: do not choose 2 and 3 together. Agent Real still needs option 3 only."
        )
    elif chosen == "1":
        lines.append(
            "IDX choice: option 1 — Matrix frame. That is website-only and does not feed this agent. "
            "Agent Real still needs option 3 (Trestle WebAPI)."
        )
    agent_id = parsed.get("mls_agent_id") or fields.get("mls_agent_id")
    if agent_id:
        lines.append(f"MLS agent ID: {agent_id}.")
    coverage = parsed.get("coverage_area") or fields.get("coverage_area")
    if _looks_like_idx_coverage(coverage):
        lines.append(f"Coverage: {coverage}.")
    statuses = parsed.get("listing_statuses") or fields.get("listing_statuses")
    if _looks_like_listing_status(statuses):
        lines.append(f"Statuses: {statuses}.")
    still = [item for item in missing if item in {"chosen_idx_option", "mls_agent_id"}]
    if still:
        need = []
        if "chosen_idx_option" in still:
            need.append("option 3 yes/no")
        if "mls_agent_id" in still:
            need.append("MLS agent ID")
        lines.append("Still need: " + " and ".join(need) + ".")
    lines.append("Relays stay on. I will not text Amos or investors.")
    return "\n".join(lines)


def _looks_like_idx_coverage(value: str | None) -> bool:
    raw = str(value or "").strip()
    if not raw or len(raw) > 120 or CONTRACT_NOISE_RE.search(raw):
        return False
    return bool(re.search(r"henderson|north las vegas|\blv\b|las vegas", raw, re.I))


def _looks_like_listing_status(value: str | None) -> bool:
    raw = str(value or "").strip()
    if not raw or len(raw) > 80 or CONTRACT_NOISE_RE.search(raw):
        return False
    return bool(re.search(r"\b(active|pending|sold|coming soon)\b", raw, re.I))


def _sanitize_idx_fields(fields: dict) -> dict:
    cleaned = {key: value for key, value in fields.items() if key in IDX_FIELD_KEYS and value}
    if not _looks_like_idx_coverage(cleaned.get("coverage_area")):
        cleaned.pop("coverage_area", None)
    if not _looks_like_listing_status(cleaned.get("listing_statuses")):
        cleaned.pop("listing_statuses", None)
    mls_name = str(cleaned.get("mls_name") or "")
    if not mls_name or len(mls_name) > 80 or CONTRACT_NOISE_RE.search(mls_name):
        cleaned["mls_name"] = PACKET_2_FROM_CAT["mls_name"]
    return cleaned


def _merge_packet2_fields(db: Session, damian: Realtor, parsed: dict) -> dict:
    fields = dict(PACKET_2_FROM_CAT)
    rows = (
        db.query(RealtorPacket)
        .filter(RealtorPacket.realtor_id == damian.id, RealtorPacket.packet_number == 2)
        .order_by(RealtorPacket.updated_at.asc())
        .all()
    )
    for row in rows:
        payload = row.payload or {}
        for key in IDX_FIELD_KEYS:
            value = payload.get(key)
            if value:
                fields[key] = value
    if parsed.get("chosen_idx_option"):
        fields["chosen_idx_option"] = parsed["chosen_idx_option"]
        fields["api_vendor"] = "Trestle (Cotality)" if parsed["chosen_idx_option"] == "3" else fields.get("api_vendor")
    if parsed.get("mls_agent_id"):
        fields["mls_agent_id"] = parsed["mls_agent_id"]
    if parsed.get("coverage_area"):
        fields["coverage_area"] = parsed["coverage_area"]
    if parsed.get("listing_statuses"):
        fields["listing_statuses"] = parsed["listing_statuses"]
    fields["telegram_idx_reply"] = parsed.get("raw")
    return fields


def _upsert_telegram_packet2(
    db: Session,
    damian: Realtor,
    fields: dict,
    missing: list[str],
    apply_result: dict,
    from_user: dict | None,
) -> RealtorPacket:
    username = str((from_user or {}).get("username") or "damianlasvegas").lstrip("@")
    message_id = f"<telegram-idx-{username}@pirateeye>"
    row = (
        db.query(RealtorPacket)
        .filter(RealtorPacket.message_id == message_id, RealtorPacket.packet_number == 2)
        .one_or_none()
    )
    if row is None:
        row = RealtorPacket(
            public_id=next_public_id(db, "PKT"),
            realtor_id=damian.id,
            packet_number=2,
            message_id=message_id,
        )
        db.add(row)
    row.realtor_id = damian.id
    row.status = PacketStatus.APPLIED.value if not missing else PacketStatus.PARTIAL.value
    row.account = "telegram"
    row.from_header = f"{DAMIAN_NAME} (@{username})"
    row.to_header = "@PirateEye_bot"
    row.subject = "Packet 2 IDX choice via Telegram"
    row.received_at = datetime.now(timezone.utc)
    row.payload = fields
    row.missing_fields = missing
    row.apply_result = apply_result
    row.notes = (fields.get("telegram_idx_reply") or "")[:4000] or None
    db.flush()
    # Keep the Cat Yee source row, but copy the choice onto the latest packet-2 payload too.
    latest = (
        db.query(RealtorPacket)
        .filter(RealtorPacket.realtor_id == damian.id, RealtorPacket.packet_number == 2)
        .order_by(RealtorPacket.updated_at.desc())
        .all()
    )
    for item in latest:
        payload = dict(item.payload or {})
        for key in ("chosen_idx_option", "mls_agent_id", "api_vendor", "mls_name"):
            if fields.get(key):
                payload[key] = fields[key]
        if _looks_like_idx_coverage(fields.get("coverage_area")):
            payload["coverage_area"] = fields["coverage_area"]
        elif not _looks_like_idx_coverage(payload.get("coverage_area")):
            payload.pop("coverage_area", None)
        if _looks_like_listing_status(fields.get("listing_statuses")):
            payload["listing_statuses"] = fields["listing_statuses"]
        elif not _looks_like_listing_status(payload.get("listing_statuses")):
            payload.pop("listing_statuses", None)
        mls_name = str(payload.get("mls_name") or "")
        if not mls_name or len(mls_name) > 80 or CONTRACT_NOISE_RE.search(mls_name):
            payload["mls_name"] = fields.get("mls_name") or PACKET_2_FROM_CAT["mls_name"]
        item.payload = payload
        item.missing_fields = _missing_for_packet(2, payload, apply_result)
        if not item.missing_fields:
            item.status = PacketStatus.APPLIED.value
        elif item.status != PacketStatus.APPLIED.value:
            item.status = PacketStatus.PARTIAL.value
    db.flush()
    return row
