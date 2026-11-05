"""Lot-level inventory and COA association for TrueHold Wellness.

SKU on-hand in stock.json is a roll-up. Lots keep kit counts, label lots,
lab lots, and the stored Certificate of Analysis for each receipt.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from wellness_agent.catalog import UnknownProductError, find_product
from wellness_agent.envfile import PACKAGE_ROOT

INVENTORY_DIR = Path(__file__).resolve().parent
PACKAGED_LOTS_PATH = INVENTORY_DIR / "lots.json"
COA_DIR = INVENTORY_DIR / "coa"

KLOW_VIALS_PER_KIT = 10


def lots_path() -> Path:
    override = os.environ.get("WELLNESS_LOTS_PATH")
    if override:
        return Path(override)
    runtime = PACKAGE_ROOT / "data" / "inventory_lots.json"
    if runtime.is_file():
        return runtime
    return PACKAGED_LOTS_PATH


def coa_dir() -> Path:
    override = os.environ.get("WELLNESS_COA_DIR")
    if override:
        return Path(override)
    return COA_DIR


def _blank() -> dict[str, Any]:
    return {"lots": [], "coas": []}


def _from_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return _blank()
    lots = payload.get("lots") if isinstance(payload.get("lots"), list) else []
    coas = payload.get("coas") if isinstance(payload.get("coas"), list) else []
    state: dict[str, Any] = {"lots": lots, "coas": coas}
    tracker = payload.get("tracker")
    if isinstance(tracker, dict):
        state["tracker"] = tracker
    return state


def load_packaged_lots() -> dict[str, Any]:
    if not PACKAGED_LOTS_PATH.is_file():
        return _blank()
    try:
        payload = json.loads(PACKAGED_LOTS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank()
    return _from_payload(payload)


def load_lots() -> dict[str, Any]:
    path = lots_path()
    if not path.is_file():
        if os.environ.get("WELLNESS_LOTS_PATH"):
            return _blank()
        if path != PACKAGED_LOTS_PATH:
            return load_packaged_lots()
        return _blank()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank()
    return _from_payload(payload)


def save_lots(state: dict[str, Any]) -> None:
    path = lots_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def lot_id_for(*, sku_id: str, coa_lot: str, label_lot: str = "") -> str:
    sku = sku_id.strip().upper()
    coa = (coa_lot or "").strip() or "NO-COA"
    label = (label_lot or "").strip()
    if label and label != coa:
        return f"{sku}-{coa}-{label}"
    return f"{sku}-{coa}"


def find_lot(lot_id: str) -> dict[str, Any] | None:
    for row in load_lots()["lots"]:
        if isinstance(row, dict) and row.get("lot_id") == lot_id:
            return row
    return None


def find_coa(coa_id: str) -> dict[str, Any] | None:
    for row in load_lots()["coas"]:
        if isinstance(row, dict) and row.get("coa_id") == coa_id:
            return row
    return None


def _positive_int(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    number = int(value)
    if number < 0:
        raise ValueError(f"{name} cannot be negative")
    return number


def receive_lot(
    sku: str,
    *,
    kits: int | None = None,
    vials: int | None = None,
    vials_per_kit: int | None = None,
    label_code: str = "",
    label_lot: str = "",
    coa_lot: str,
    received_at: str | None = None,
    notes: str = "",
    coa: dict[str, Any] | None = None,
    apply_on_hand: bool = True,
) -> dict[str, Any]:
    """Record a physical receipt, associate a COA, and increment on-hand vials."""
    item = find_product(sku)
    per_kit = _positive_int(vials_per_kit, "vials_per_kit")
    if per_kit is None:
        per_kit = KLOW_VIALS_PER_KIT if item["id"] == "klow" else 1
    kit_count = _positive_int(kits, "kits")
    vial_count = _positive_int(vials, "vials")
    if kit_count is None and vial_count is None:
        raise ValueError("Provide kits and/or vials")
    if kit_count is not None and vial_count is None:
        vial_count = kit_count * per_kit
    elif vial_count is not None and kit_count is None:
        if vial_count % per_kit != 0:
            raise ValueError(
                f"{vial_count} vials is not a whole number of {per_kit}-vial kits"
            )
        kit_count = vial_count // per_kit
    elif kit_count * per_kit != vial_count:
        raise ValueError(
            f"{kit_count} kits × {per_kit} vials/kit = {kit_count * per_kit}, not {vial_count}"
        )
    if vial_count < 1:
        raise ValueError("vials must be at least 1")

    coa_lot_text = str(coa_lot or "").strip()
    if not coa_lot_text:
        raise ValueError("coa_lot is required")
    label_lot_text = str(label_lot or "").strip()
    label_code_text = str(label_code or "").strip()
    lot_id = lot_id_for(sku_id=item["id"], coa_lot=coa_lot_text, label_lot=label_lot_text)
    existing = find_lot(lot_id)
    if existing is not None:
        return {"ok": True, "duplicate": True, "lot": existing}

    received = (received_at or date.today().isoformat()).strip()
    coa_payload = dict(coa or {})
    coa_id = str(coa_payload.get("coa_id") or coa_lot_text).strip()
    coa_payload.setdefault("coa_id", coa_id)
    coa_payload.setdefault("lot", coa_lot_text)
    coa_payload.setdefault("sku_id", item["id"])
    coa_payload.setdefault("associated_lot_ids", [lot_id])

    state = load_lots()
    existing_coa = next(
        (row for row in state["coas"] if isinstance(row, dict) and row.get("coa_id") == coa_id),
        None,
    )
    if existing_coa is None:
        state["coas"].append(coa_payload)
    else:
        linked = list(existing_coa.get("associated_lot_ids") or [])
        if lot_id not in linked:
            linked.append(lot_id)
        existing_coa["associated_lot_ids"] = linked
        for key, value in coa_payload.items():
            if key == "associated_lot_ids":
                continue
            if value not in (None, "", [], {}) and not existing_coa.get(key):
                existing_coa[key] = value
        coa_id = str(existing_coa.get("coa_id") or coa_id)

    lot_row = {
        "lot_id": lot_id,
        "received_at": received,
        "timezone": "America/Los_Angeles",
        "sku_id": item["id"],
        "name": item["name"],
        "strength": item.get("vial") or "",
        "kits_received": kit_count,
        "vials_per_kit": per_kit,
        "vials_received": vial_count,
        "vials_on_hand": vial_count,
        "label_code": label_code_text,
        "label_lot": label_lot_text,
        "coa_lot": coa_lot_text,
        "coa_id": coa_id,
        "status": "in_stock",
        "notes": notes.strip(),
    }
    state["lots"].append(lot_row)
    save_lots(state)

    on_hand = None
    if apply_on_hand:
        from wellness_agent.stock import receive_stock

        entry = receive_stock(
            item["id"],
            vial_count,
            reason="lot-receipt",
            detail=lot_id,
        )
        on_hand = entry.get("on_hand")
    return {"ok": True, "duplicate": False, "lot": lot_row, "on_hand": on_hand}


def vials_on_hand_from_lots(sku: str) -> int | None:
    total = 0
    found = False
    for row in load_lots()["lots"]:
        if not isinstance(row, dict) or row.get("sku_id") != sku:
            continue
        if row.get("status") not in (None, "", "in_stock"):
            continue
        found = True
        total += int(row.get("vials_on_hand") or 0)
    return total if found else None


def format_lots() -> str:
    state = load_lots()
    lines = ["TrueHold Wellness lots and COAs", ""]
    if not state["lots"]:
        lines.append("No lots recorded.")
        return "\n".join(lines) + "\n"
    coas = {row.get("coa_id"): row for row in state["coas"] if isinstance(row, dict)}
    for row in state["lots"]:
        if not isinstance(row, dict):
            continue
        kits = row.get("kits_received")
        vials = row.get("vials_on_hand")
        received = row.get("vials_received")
        lines.append(
            f"• {row.get('name')} {row.get('lot_id')} — "
            f"{kits} kits / {received} vials received, {vials} on hand"
        )
        lines.append(
            f"  label {row.get('label_code') or '—'} / {row.get('label_lot') or '—'}; "
            f"COA lot {row.get('coa_lot') or '—'}"
        )
        coa = coas.get(row.get("coa_id")) or {}
        purity = coa.get("purity_percent")
        file_name = coa.get("file") or ""
        extra = []
        if purity is not None:
            extra.append(f"purity {purity}%")
        if coa.get("lab"):
            extra.append(str(coa["lab"]))
        if file_name:
            extra.append(str(file_name))
        if extra:
            lines.append("  " + " · ".join(extra))
        if row.get("notes"):
            lines.append(f"  {row['notes']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_stock_with_lots() -> str:
    from wellness_agent.stock import format_stock

    return format_stock().rstrip() + "\n\n" + format_lots()
