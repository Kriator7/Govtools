"""Parse inbound TrueHold Wellness order emails. Not realtor listings."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_inbox(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8") or "[]")
    if isinstance(payload, list):
        return payload
    return list(payload.get("messages") or [])


def parse_order_email(raw: dict[str, Any]) -> dict[str, Any]:
    subject = str(raw.get("subject") or "").strip()
    body = str(raw.get("body") or "").strip()
    from_address = str(raw.get("from") or raw.get("from_address") or "").strip()
    product = _field(body, "product") or _product_from_subject(subject)
    quantity = _int_field(body, "quantity") or _quantity_from_subject(subject)
    customer = _field(body, "customer") or _field(body, "name") or str(raw.get("customer_name") or "") or None
    return {
        "from_address": from_address or "unknown",
        "subject": subject or "(no subject)",
        "body": body,
        "customer_name": customer,
        "product": product,
        "quantity": quantity,
        "source_message_id": str(raw.get("message_id") or raw.get("id") or ""),
    }


def _field(body: str, name: str) -> str | None:
    match = re.search(rf"^{name}\s*[:=]\s*(.+)$", body, flags=re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _int_field(body: str, name: str) -> int | None:
    value = _field(body, name)
    if value and value.isdigit():
        return int(value)
    return None


def _product_from_subject(subject: str) -> str | None:
    match = re.search(r"order[:\s]+(.+)$", subject, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _quantity_from_subject(subject: str) -> int | None:
    match = re.search(r"\b(\d+)\s*x\b", subject, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None
