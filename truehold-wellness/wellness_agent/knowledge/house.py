"""TrueHold Wellness house knowledge: one approved DB every host reads.

Educational kitchen, fasting, and prep-state notes only. Mix math, dosing,
reconstitution, and injection stay on the locked sheet — never in chat.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

HOUSE_PATH = Path(__file__).resolve().parent / "house.json"

WEIGHT_LOSS_IDS = frozenset({"tirzepatide", "retatrutide"})
FASTING_OPENER = "Have you ever fasted before?"


@lru_cache
def load_house() -> dict[str, Any]:
    return json.loads(HOUSE_PATH.read_text(encoding="utf-8"))


def house_experience() -> str:
    return str((load_house().get("house") or {}).get("experience") or "")


def host_bio(member_id: str) -> dict[str, str]:
    row = (load_house().get("bios") or {}).get(str(member_id) or "") or {}
    return {
        "short": str(row.get("short") or ""),
        "bio": str(row.get("bio") or ""),
        "herbs": str(row.get("herbs") or ""),
    }


def fasting() -> dict[str, str]:
    row = load_house().get("fasting") or {}
    return {str(key): str(value) for key, value in row.items()}


def herbs() -> list[dict[str, Any]]:
    return list(load_house().get("herbs") or [])


def peptide_record(product_id: str) -> dict[str, Any]:
    row = (load_house().get("peptides") or {}).get(str(product_id) or "") or {}
    opener = str(row.get("opener") or "What are you hoping this tool will support?")
    if product_id in WEIGHT_LOSS_IDS:
        opener = FASTING_OPENER
    return {
        "id": product_id,
        "family": str(row.get("family") or "research"),
        "opener": opener,
        "prep": str(row.get("prep") or "Sleep, water, protein, and a calm kitchen first. Mix math stays on the locked sheet."),
        "herbs": [str(item) for item in (row.get("herbs") or [])],
        "fasting": bool(row.get("fasting") or product_id in WEIGHT_LOSS_IDS),
        "weight_loss": product_id in WEIGHT_LOSS_IDS,
    }


def herb_line(herb_id: str) -> str:
    for row in herbs():
        if str(row.get("id")) == herb_id:
            name = str(row.get("name") or herb_id)
            note = str(row.get("note") or "")
            return f"{name} — {note}".strip(" —")
    return ""


def companion_herbs(product_id: str) -> str:
    names = []
    wanted = set(peptide_record(product_id)["herbs"])
    for row in herbs():
        if str(row.get("id")) in wanted:
            names.append(str(row.get("name") or row["id"]))
    return ", ".join(names)


def seed_rows() -> list[tuple[str, str, str, str]]:
    """Rows for snippets: id, kind, title, text."""
    rows: list[tuple[str, str, str, str]] = []
    house = load_house().get("house") or {}
    rows.append(
        (
            "house-experience",
            "house",
            "The TrueHold team",
            str(house.get("experience") or "")
            + " "
            + str(house.get("stance") or ""),
        )
    )
    fast = fasting()
    rows.append(
        (
            "fasting-core",
            "fasting",
            str(fast.get("title") or "Intermittent fasting"),
            " ".join(
                str(fast.get(key) or "")
                for key in ("summary", "how", "weight_loss", "caution")
            ),
        )
    )
    for herb in herbs():
        herb_id = str(herb.get("id") or "")
        if not herb_id:
            continue
        pairs = ", ".join(str(item) for item in (herb.get("pairs") or []))
        text = f"{herb.get('name')}: {herb.get('note')} Kitchen/educational only. Often discussed with: {pairs}.".strip()
        rows.append((f"herb-{herb_id}", "herb", str(herb.get("name") or herb_id), text))
    for product_id, row in (load_house().get("peptides") or {}).items():
        rec = peptide_record(str(product_id))
        companions = companion_herbs(str(product_id))
        herb_bit = f" Kitchen allies often discussed: {companions}." if companions else ""
        text = (
            f"{product_id}: opener “{rec['opener']}” "
            f"Prep state: {rec['prep']}"
            f"{herb_bit} Mix math stays on the locked sheet. Educational only."
        )
        rows.append((f"prep-{product_id}", "prep", f"{product_id} prep", text))
    for member_id, row in (load_house().get("bios") or {}).items():
        bio = str(row.get("bio") or "")
        short = str(row.get("short") or "")
        herbs_home = str(row.get("herbs") or "")
        text = f"{short} {bio} Home herbal study: {herbs_home} {house_experience()}"
        rows.append((f"bio-{member_id}", "bio", f"{member_id} bio", text.strip()))
    return rows


def format_prep_caption(product: dict[str, Any]) -> str:
    rec = peptide_record(str(product.get("id") or ""))
    companions = companion_herbs(rec["id"])
    lines = [
        f"<b>{product.get('name') or rec['id']}</b>",
        str(product.get("vial") or ""),
        "",
        "<b>Prep state</b>",
        rec["prep"],
    ]
    if companions:
        lines.extend(["", "<b>Kitchen allies</b>", companions, "Educational herbs and food — not a prescription."])
    lines.extend(["", f"<b>{rec['opener']}</b>"])
    if rec["weight_loss"]:
        lines.append("Fasting is the ideal prep conversation for this vial.")
    lines.extend(["", "Las Vegas · dry vials only · mix math on Sheet"])
    return "\n".join(line for line in lines if line is not None)


def format_fasting_followup(*, experienced: bool) -> str:
    fast = fasting()
    if experienced:
        body = str(fast.get("if_yes") or fast.get("summary") or "")
    else:
        body = str(fast.get("if_no") or fast.get("summary") or "")
    caution = str(fast.get("caution") or "")
    return f"<b>Intermittent fasting</b>\n{body}\n\n<i>{caution}</i>".strip()


def format_host_bio(member: dict[str, Any]) -> str:
    row = host_bio(str(member.get("id") or ""))
    experience = house_experience()
    parts = [
        f"<b>{member.get('icon')} {member.get('name')}</b> · {member.get('role')}",
        row.get("bio") or row.get("short") or str(member.get("creed") or ""),
    ]
    if row.get("herbs"):
        parts.append(f"<b>Home herbal study</b>\n{row['herbs']}")
    if experience:
        parts.append(experience)
    parts.append("Educational only. Mix math stays on the locked sheet.")
    return "\n\n".join(part for part in parts if part)
