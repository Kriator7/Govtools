"""Write a gitignored snapshot of which packets arrived."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.realtor_packet import RealtorPacket
from app.services.seed import DAMIAN_BROKERAGE, DAMIAN_EMAIL, DAMIAN_NAME


PACKET_TITLES = {
    1: "Who you are",
    2: "MLS / listing access",
    3: "Investor list",
    4: "Investor buy boxes",
    5: "Realtor alerts",
    6: "Investor notifications",
    7: "Forms",
    8: "Transaction / e-sign platform",
    9: "Sample closed deals",
    10: "Office rules",
}


def write_intake_snapshot(db: Session, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    rows = db.query(RealtorPacket).order_by(RealtorPacket.packet_number.asc(), RealtorPacket.created_at.asc()).all()
    by_packet: dict[int, list[RealtorPacket]] = {}
    for row in rows:
        by_packet.setdefault(row.packet_number, []).append(row)
    lines = [
        f"# Damian packet intake snapshot",
        "",
        f"Watch address: `{settings.imap_watch_address}`",
        f"Live realtor target: {DAMIAN_NAME} / {DAMIAN_BROKERAGE} (`{DAMIAN_EMAIL}`)",
        "",
        "SMS and email relays stay on. This snapshot is written by `inbox-poll`.",
        "",
        "| Packet | Title | Status | From | Subject | Missing |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for number in range(1, 11):
        title = PACKET_TITLES[number]
        packet_rows = by_packet.get(number) or []
        if not packet_rows:
            lines.append(f"| {number} | {title} | waiting | — | — | — |")
            continue
        latest = packet_rows[-1]
        missing = ", ".join(latest.missing_fields or []) or "—"
        subject = (latest.subject or "—").replace("|", "/")
        sender = (latest.from_header or "—").replace("|", "/")
        lines.append(f"| {number} | {title} | {latest.status} | {sender} | {subject} | {missing} |")
    unclassified = by_packet.get(0) or []
    if unclassified:
        lines.extend(["", "## Unclassified Damian mail", ""])
        for row in unclassified:
            lines.append(f"- `{row.status}` {row.from_header} — {row.subject}")
    path = settings.project_root / "data" / "packets" / "STATUS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
