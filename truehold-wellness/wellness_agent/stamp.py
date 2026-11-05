"""Inventory / lot / client stamp emailed to TrueHold Wellness on each invoice.

The stamp is the current-state confirmation: SKU on-hand, lots, and the client
list with every email, mobile, and text field we have — plus the gaps we still
need so reorder outreach can happen by text and email.
"""

from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from wellness_agent.envfile import PACKAGE_ROOT
from wellness_agent.telegram_copy import TEAM_EMAIL

PACIFIC = ZoneInfo("America/Los_Angeles")
PACKAGED_ROSTER_PATH = (
    Path(__file__).resolve().parent / "inventory" / "clients_roster.json"
)
STAMP_TO_ENV = "WELLNESS_STAMP_TO"
STAMP_FROM_ENV = "WELLNESS_STAMP_FROM"
SMTP_HOST_ENV = "WELLNESS_SMTP_HOST"
SMTP_PORT_ENV = "WELLNESS_SMTP_PORT"
SMTP_USER_ENV = "WELLNESS_SMTP_USERNAME"
SMTP_PASS_ENV = "WELLNESS_SMTP_PASSWORD"
SMTP_STARTTLS_ENV = "WELLNESS_SMTP_STARTTLS"


def roster_path() -> Path:
    override = os.environ.get("WELLNESS_CLIENTS_ROSTER_PATH")
    if override:
        return Path(override)
    runtime = PACKAGE_ROOT / "data" / "clients_roster.json"
    if runtime.is_file():
        return runtime
    return PACKAGED_ROSTER_PATH


def stamp_log_path() -> Path:
    override = os.environ.get("WELLNESS_STAMP_LOG_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / "stamp_log.jsonl"


def pacific_now() -> datetime:
    return datetime.now(tz=PACIFIC)


def stamp_subject(*, when: datetime | None = None, invoice_id: str = "") -> str:
    stamp = (when or pacific_now()).strftime("%Y-%m-%d %H:%M %Z")
    if invoice_id:
        return f"TrueHold Wellness invoice stamp {invoice_id} — inventory, lots, clients {stamp}"
    return f"TrueHold Wellness current state — inventory, lots, clients {stamp}"


def load_roster() -> dict[str, Any]:
    path = roster_path()
    if not path.is_file():
        if os.environ.get("WELLNESS_CLIENTS_ROSTER_PATH"):
            return {"clients": []}
        if path != PACKAGED_ROSTER_PATH and PACKAGED_ROSTER_PATH.is_file():
            path = PACKAGED_ROSTER_PATH
        else:
            return {"clients": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"clients": []}
    clients = payload.get("clients") if isinstance(payload, dict) else None
    if not isinstance(clients, list):
        return {"clients": []}
    return {
        "as_of": payload.get("as_of"),
        "timezone": payload.get("timezone") or "America/Los_Angeles",
        "purpose": payload.get("purpose") or "",
        "clients": [row for row in clients if isinstance(row, dict)],
    }


def _blank(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "NOT ON FILE"


def _sku_totals(lots: list[dict[str, Any]]) -> list[tuple[str, str, int]]:
    totals: dict[tuple[str, str], int] = {}
    order: list[tuple[str, str]] = []
    for row in lots:
        if row.get("status") not in (None, "", "in_stock"):
            continue
        name = str(row.get("name") or row.get("sku_id") or "").strip()
        strength = str(row.get("strength") or "").strip() or "unspecified"
        key = (name, strength)
        if key not in totals:
            order.append(key)
            totals[key] = 0
        totals[key] += int(row.get("vials_on_hand") or 0)
    return [(name, strength, totals[(name, strength)]) for name, strength in order]


def _telegram_clients() -> list[dict[str, Any]]:
    from wellness_agent.clients import list_telegram_clients

    extras: list[dict[str, Any]] = []
    for row in list_telegram_clients():
        chat_id = str(row.get("chat_id") or "")
        name = str(row.get("name") or "").strip() or f"Telegram {chat_id}"
        phone = str(row.get("phone") or "").strip()
        extras.append(
            {
                "client_id": f"THW-TG-{chat_id}",
                "name": name,
                "email": "",
                "phone": phone,
                "sms": phone,
                "last_purchase": "",
                "due_for": "Collect email if missing",
                "contact_gaps": ["email"] + ([] if phone else ["phone", "sms"]),
                "status": "telegram",
                "source": f"Telegram chat {chat_id}",
                "notes": "Phone captured in Telegram. Email not stored on this record.",
            }
        )
    return extras


def stamp_payload(*, invoice_id: str = "", reason: str = "") -> dict[str, Any]:
    from wellness_agent.inventory.lots import load_lots, load_packaged_lots
    from wellness_agent.stock import load_stock

    lots_state = load_lots()
    if not lots_state.get("lots") and not os.environ.get("WELLNESS_LOTS_PATH"):
        lots_state = load_packaged_lots()
    lots = [row for row in lots_state.get("lots", []) if isinstance(row, dict)]
    roster = load_roster()
    clients = list(roster["clients"]) + _telegram_clients()
    when = pacific_now()
    sku_totals = _sku_totals(lots)
    missing = [
        row
        for row in clients
        if not str(row.get("email") or "").strip() or not str(row.get("phone") or row.get("sms") or "").strip()
    ]
    return {
        "kind": "truehold-wellness-invoice-stamp",
        "generated_at": when.isoformat(),
        "timezone": "America/Los_Angeles",
        "invoice_id": invoice_id or "",
        "reason": reason or "current-state",
        "to": os.environ.get(STAMP_TO_ENV, TEAM_EMAIL),
        "tracker": lots_state.get("tracker") or {},
        "sku_totals": [
            {"name": name, "strength": strength, "vials_on_hand": count}
            for name, strength, count in sku_totals
        ],
        "vials_on_hand_total": sum(count for _, _, count in sku_totals),
        "stock": load_stock().get("products") or {},
        "lots": lots,
        "clients": clients,
        "contact_gaps": [
            {
                "client_id": row.get("client_id"),
                "name": row.get("name"),
                "missing": row.get("contact_gaps")
                or [
                    field
                    for field in ("email", "phone", "sms")
                    if not str(row.get(field) or "").strip()
                ],
            }
            for row in missing
        ],
        "client_count": len(clients),
        "gap_count": len(missing),
    }


def format_stamp(payload: dict[str, Any] | None = None) -> str:
    data = payload or stamp_payload()
    when = data.get("generated_at") or pacific_now().isoformat()
    invoice = data.get("invoice_id") or "(no invoice — current-state snapshot)"
    reason = data.get("reason") or "current-state"
    tracker = data.get("tracker") or {}
    lines = [
        "TrueHold Wellness — inventory / lots / client stamp",
        "",
        f"Generated: {when} (America/Los_Angeles)",
        f"Invoice / event: {invoice}",
        f"Reason: {reason}",
        f"This email is the confirmation copy. It stamps current inventory, lots, and the client list.",
        "",
        "ACTION: Collect mobile (text) and email for every client who is missing them so we can contact them for reorder.",
        "",
        "Tracker",
        f"• Folder: {tracker.get('drive_folder') or 'not set'}",
        f"• Lots: {tracker.get('lots_sheet') or 'not set'}",
        f"• COAs: {tracker.get('coa_sheet') or 'not set'}",
        f"• Clients: {tracker.get('clients_sheet') or 'not set'}",
        f"• Logs: {tracker.get('logs_sheet') or 'not set'}",
        "",
        f"On-hand inventory ({data.get('vials_on_hand_total', 0)} vials, all SKUs)",
    ]
    totals = data.get("sku_totals") or []
    if not totals:
        lines.append("• No lot on-hand totals recorded.")
    for row in totals:
        lines.append(
            f"• {row.get('name')} — {row.get('vials_on_hand')} on hand ({row.get('strength')})"
        )
    lines.extend(["", "Lots"])
    lots = data.get("lots") or []
    if not lots:
        lines.append("• No lots recorded.")
    for lot in lots:
        kits = lot.get("kits_received")
        kit_word = "kit" if kits == 1 else "kits"
        lines.append(
            f"• {lot.get('name')} {lot.get('lot_id')} — {kits} {kit_word} / "
            f"{lot.get('vials_received')} received, {lot.get('vials_on_hand')} on hand "
            f"({lot.get('strength') or 'strength not set'})"
        )
        lines.append(
            f"  label {lot.get('label_code') or '—'} / {lot.get('label_lot') or '—'}; "
            f"kit {lot.get('kit_code') or '—'}; COA {lot.get('coa_lot') or '—'} "
            f"({lot.get('coa_id') or '—'})"
        )
    lines.extend(
        [
            "",
            f"Client list ({data.get('client_count', 0)}) — contact for reorder",
        ]
    )
    clients = data.get("clients") or []
    if not clients:
        lines.append("• No clients on the roster yet.")
    for row in clients:
        gaps = row.get("contact_gaps") or []
        gap_text = ", ".join(str(item) for item in gaps) if gaps else "none"
        lines.extend(
            [
                f"• {row.get('name')} ({row.get('client_id') or 'no id'}; {row.get('status') or 'unknown'})",
                f"  Email: {_blank(row.get('email'))}"
                + (f" | alt {_blank(row.get('email_alt'))}" if row.get("email_alt") else ""),
                f"  Mobile / text: {_blank(row.get('phone') or row.get('sms'))}",
                f"  Last purchase: {_blank(row.get('last_purchase'))}"
                + (f" on {row['last_purchase_date']}" if row.get("last_purchase_date") else ""),
                f"  Due for: {_blank(row.get('due_for'))}",
                f"  Still need: {gap_text}",
            ]
        )
        if row.get("notes"):
            lines.append(f"  Notes: {row['notes']}")
    lines.extend(
        [
            "",
            f"Contact gaps ({data.get('gap_count', 0)}) — collect before reorder blast",
        ]
    )
    gaps = data.get("contact_gaps") or []
    if not gaps:
        lines.append("• Every listed client has both email and mobile on file.")
    for row in gaps:
        missing = ", ".join(str(item) for item in (row.get("missing") or [])) or "unspecified"
        lines.append(f"• {row.get('name')}: missing {missing}")
    lines.extend(
        [
            "",
            "Do not invent prices, lot numbers, emails, or phone numbers.",
            "Demo/test Telegram numbers and James's own shop-test orders are not on this roster.",
        ]
    )
    return "\n".join(lines) + "\n"


def append_stamp_log(payload: dict[str, Any], *, status: str) -> Path:
    path = stamp_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": payload.get("generated_at"),
        "invoice_id": payload.get("invoice_id"),
        "reason": payload.get("reason"),
        "status": status,
        "to": payload.get("to"),
        "vials_on_hand_total": payload.get("vials_on_hand_total"),
        "client_count": payload.get("client_count"),
        "gap_count": payload.get("gap_count"),
        "subject": stamp_subject(
            when=datetime.fromisoformat(str(payload["generated_at"]))
            if payload.get("generated_at")
            else None,
            invoice_id=str(payload.get("invoice_id") or ""),
        ),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    return path


def _smtp_settings() -> dict[str, Any] | None:
    username = (os.environ.get(SMTP_USER_ENV) or os.environ.get(STAMP_FROM_ENV) or "").strip()
    password = (os.environ.get(SMTP_PASS_ENV) or "").replace(" ", "")
    if not username or not password:
        return None
    starttls_raw = os.environ.get(SMTP_STARTTLS_ENV, "1").strip().lower()
    return {
        "host": os.environ.get(SMTP_HOST_ENV, "smtp.gmail.com"),
        "port": int(os.environ.get(SMTP_PORT_ENV, "587")),
        "username": username,
        "password": password,
        "starttls": starttls_raw not in {"0", "false", "no"},
    }


def send_stamp_email(
    *,
    invoice_id: str = "",
    reason: str = "",
    dry_run: bool = False,
    opener: Any = None,
) -> dict[str, Any]:
    """Build the stamp and email trueholdwellness@gmail.com when SMTP is configured.

    SMTP: https://developers.google.com/workspace/gmail/imap/imap-smtp
    App passwords: https://support.google.com/accounts/answer/185833
    """
    payload = stamp_payload(invoice_id=invoice_id, reason=reason)
    body = format_stamp(payload)
    subject = stamp_subject(
        when=datetime.fromisoformat(payload["generated_at"]),
        invoice_id=invoice_id,
    )
    destination = str(payload["to"] or TEAM_EMAIL)
    sender = os.environ.get(STAMP_FROM_ENV, os.environ.get(SMTP_USER_ENV, TEAM_EMAIL)).strip() or TEAM_EMAIL
    result = {
        "ok": True,
        "subject": subject,
        "to": destination,
        "from": sender,
        "body": body,
        "payload": payload,
        "status": "dry_run",
        "delivered": False,
    }
    if dry_run:
        append_stamp_log(payload, status="dry_run")
        return result
    settings = _smtp_settings()
    if settings is None:
        result["status"] = "queued_no_smtp"
        result["error"] = (
            f"No {SMTP_PASS_ENV} configured. Stamp was logged; email was not sent. "
            "Set WELLNESS_SMTP_USERNAME and WELLNESS_SMTP_PASSWORD (Gmail app password)."
        )
        append_stamp_log(payload, status="queued_no_smtp")
        return result
    message = EmailMessage()
    message["From"] = sender
    message["To"] = destination
    message["Subject"] = subject
    message.set_content(body)
    send = opener or _smtp_send
    send(settings, message)
    result["status"] = "sent"
    result["delivered"] = True
    append_stamp_log(payload, status="sent")
    return result


def _smtp_send(settings: dict[str, Any], message: EmailMessage) -> None:
    if int(settings["port"]) == 465 and not settings["starttls"]:
        client: smtplib.SMTP = smtplib.SMTP_SSL(settings["host"], int(settings["port"]), timeout=20)
    else:
        client = smtplib.SMTP(settings["host"], int(settings["port"]), timeout=20)
        client.ehlo()
        if settings["starttls"]:
            client.starttls()
            client.ehlo()
    try:
        client.login(settings["username"], settings["password"])
        client.send_message(message)
    finally:
        try:
            client.quit()
        except Exception:
            client.close()


def stamp_after_invoice(*, invoice_id: str, reason: str = "invoice") -> dict[str, Any]:
    """Standard operation: stamp current inventory/lots/clients after an invoice or order."""
    return send_stamp_email(invoice_id=invoice_id, reason=reason, dry_run=False)
