"""Classify inbound TrueHold Wellness emails into the original inbox-reflex categories."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from wellness_agent.catalog import products
from wellness_agent.envfile import PACKAGE_ROOT
from wellness_agent.reflex import fire_reflex

# Original Wellness inbox reflexes. Crypto/Hormuz is out of scope.
REFLEX_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "cancellation",
        ("cancel", "cancellation", "refund", "chargeback"),
    ),
    (
        "payment",
        ("payment", "paid", "invoice", "receipt", "card declined"),
    ),
    (
        "shipping",
        ("shipping", "shipped", "tracking", "delivery", "usps", "ups", "fedex"),
    ),
    (
        "fulfillment",
        ("fulfillment", "fulfilment", "pack the", "ready to ship", "pick list"),
    ),
    (
        "peptide",
        ("peptide",),
    ),
    (
        "order",
        ("order", "purchase", "qty", "quantity", "interest order"),
    ),
)


def seen_path() -> Path:
    override = os.environ.get("WELLNESS_EMAIL_SEEN_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / "email_seen.json"


def _load_seen() -> set[str]:
    path = seen_path()
    if not path.is_file():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {str(item) for item in payload.get("ids") or []}


def _save_seen(ids: set[str]) -> None:
    path = seen_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"ids": sorted(ids)}, indent=2), encoding="utf-8")


def classify_email(raw: dict[str, Any]) -> str:
    blob = f"{raw.get('subject') or ''} {raw.get('body') or ''}".lower()
    sku_names = tuple(item["name"].lower() for item in products()) + tuple(
        alias.lower() for item in products() for alias in item["aliases"]
    )
    if any(name and name in blob for name in sku_names) and not any(
        word in blob for word in ("cancel", "refund", "payment", "ship", "tracking")
    ):
        if any(word in blob for word in ("order", "purchase", "qty", "quantity")):
            return "order"
        return "peptide"
    for trigger, keywords in REFLEX_KEYWORDS:
        if any(keyword in blob for keyword in keywords):
            return trigger
    return "business"


def _detail(raw: dict[str, Any], trigger: str) -> str:
    subject = str(raw.get("subject") or "(no subject)").strip()
    sender = str(raw.get("from") or raw.get("from_address") or "unknown").strip()
    body = str(raw.get("body") or "").strip()
    excerpt = " ".join(body.split())[:240]
    return f"New TrueHold Wellness {trigger} email from {sender}: {subject}. {excerpt}".strip()


def ingest_reflex_emails(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8") or "[]")
    messages = payload if isinstance(payload, list) else list(payload.get("messages") or [])
    seen = _load_seen()
    fired: list[dict[str, Any]] = []
    for raw in messages:
        source_id = str(raw.get("id") or raw.get("message_id") or "")
        if source_id and source_id in seen:
            continue
        trigger = classify_email(raw)
        detail = _detail(raw, trigger)
        result = fire_reflex(trigger, detail, require_destination=False)
        if source_id:
            seen.add(source_id)
        fired.append(
            {
                "id": source_id,
                "trigger": trigger,
                "status": result.status,
                "destination": result.destination,
            }
        )
    _save_seen(seen)
    return fired
