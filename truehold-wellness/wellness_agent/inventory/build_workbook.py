"""Build the TrueHold Wellness orders workbook (all live SKUs + inbox columns).

This is the staff ledger the old Telegram agent sent as trueholdwellness-orders.xlsx.
Drop a Finder copy into data/imports/legacy/ and run `python -m wellness_agent ingest-files`
to replace this template with the live sheet.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from wellness_agent.catalog import products
from wellness_agent.inventory.lots import load_packaged_lots

ROOT = Path(__file__).resolve().parent
WORKBOOK_DIR = ROOT / "workbooks"
WORKBOOK_PATH = WORKBOOK_DIR / "trueholdwellness-orders.xlsx"

NAVY = "092B57"
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
HEADER_FONT = Font(color="FFFFFF", bold=True, name="Calibri", size=11)
TITLE_FONT = Font(color=NAVY, bold=True, name="Calibri", size=16)
WRAP = Alignment(wrap_text=True, vertical="top")


def _header(ws: Worksheet, headers: list[str]) -> None:
    ws.append(headers)
    for col, _ in enumerate(headers, start=1):
        cell = ws.cell(1, col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(col)].width = 22
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"
    ws.freeze_panes = "A2"


def _sheet(wb: Workbook, title: str, headers: list[str], rows: list[list[object]]) -> Worksheet:
    ws = wb.create_sheet(title)
    _header(ws, headers)
    for row in rows:
        ws.append(row)
        for col in range(1, len(headers) + 1):
            ws.cell(ws.max_row, col).alignment = WRAP
    return ws


def build_workbook(dest: Path | None = None) -> Path:
    dest = dest or WORKBOOK_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    cover = wb.active
    cover.title = "How to use"
    cover["A1"] = "TrueHold Wellness — orders & inventory ledger"
    cover["A1"].font = TITLE_FONT
    lines = [
        "",
        "This workbook is the staff ledger for @THWellness_bot.",
        "It covers every live shop SKU plus the original inbox columns:",
        "orders, payments, fulfillment, shipping, cancellations, peptides.",
        "",
        "Replace with the old-agent file from Finder:",
        "1. Telegram → Deleted Account chat → Files → Show in Finder",
        "2. Copy trueholdwellness-orders.xlsx and the PDFs",
        "3. Paste into truehold-wellness/data/imports/legacy/",
        "4. Run: python -m wellness_agent ingest-files",
        "",
        "Policy: prep and local delivery for Las Vegas residents only.",
        "Shipping is dry (lyophilized) vials only.",
        "The team calls to confirm, consult, and complete required documentation.",
        "",
        "Fill Inventory.on_hand with live vial counts, then ingest-files.",
        "Telegram interest orders decrement on-hand the same way as before.",
        "Leave on_hand blank until you have a real count — do not invent stock.",
        "Lots and COAs tabs store kit receipts, label lots, lab lots, and COA files.",
        "CLI: python -m wellness_agent receive-stock  and  python -m wellness_agent lots",
    ]
    for idx, line in enumerate(lines, start=2):
        cover[f"A{idx}"] = line
        cover[f"A{idx}"].alignment = WRAP
    cover.column_dimensions["A"].width = 88

    inventory_rows = [
        [
            item["id"],
            item["name"],
            item["vial"],
            "Dry (lyophilized) vial",
            item["category"],
            item["pdf"],
            item["shop_url"],
            "Las Vegas prep/delivery; dry-vial ship only",
            None,
        ]
        for item in products()
    ]
    _sheet(
        wb,
        "Inventory",
        ["sku_id", "name", "vial", "form", "category", "pdf", "shop_url", "fulfillment", "on_hand"],
        inventory_rows,
    )
    _sheet(
        wb,
        "Orders",
        [
            "order_id",
            "received_at",
            "customer_name",
            "phone",
            "sku_id",
            "qty",
            "status",
            "fulfillment",
            "documentation",
            "notes",
        ],
        [
            [
                "THW-TEMPLATE-000001",
                "",
                "",
                "",
                "semax",
                1,
                "interest",
                "Las Vegas local prep/delivery or dry-vial ship",
                "pending",
                "Replace this sample row. Do not invent customer data.",
            ]
        ],
    )
    _sheet(
        wb,
        "Payments",
        ["order_id", "status", "amount", "method", "notes"],
        [],
    )
    _sheet(
        wb,
        "Fulfillment",
        ["order_id", "type", "status", "las_vegas_resident", "dry_vial_only", "notes"],
        [],
    )
    _sheet(
        wb,
        "Shipping",
        ["order_id", "carrier", "tracking", "status", "dry_vial_only", "notes"],
        [],
    )
    _sheet(
        wb,
        "Cancellations",
        ["order_id", "reason", "refund_status", "notes"],
        [],
    )
    _sheet(
        wb,
        "Peptides",
        ["received_at", "source", "sku_id", "summary", "action"],
        [],
    )
    lot_rows = []
    packaged_lots = load_packaged_lots()
    for row in packaged_lots.get("lots") or []:
        if not isinstance(row, dict):
            continue
        lot_rows.append(
            [
                row.get("lot_id"),
                row.get("received_at"),
                row.get("sku_id"),
                row.get("name"),
                row.get("strength"),
                row.get("kit_code"),
                row.get("kits_received"),
                row.get("vials_per_kit"),
                row.get("vials_received"),
                row.get("vials_on_hand"),
                row.get("label_code"),
                row.get("label_lot"),
                row.get("coa_lot"),
                row.get("coa_id"),
                row.get("status"),
                row.get("notes"),
            ]
        )
    _sheet(
        wb,
        "Lots",
        [
            "lot_id",
            "received_at",
            "sku_id",
            "name",
            "strength",
            "kit_code",
            "kits_received",
            "vials_per_kit",
            "vials_received",
            "vials_on_hand",
            "label_code",
            "label_lot",
            "coa_lot",
            "coa_id",
            "status",
            "notes",
        ],
        lot_rows,
    )
    coa_rows = []
    for row in packaged_lots.get("coas") or []:
        if not isinstance(row, dict):
            continue
        net = row.get("net_content_mg") or {}
        net_text = ", ".join(f"{name} {mg} mg" for name, mg in net.items()) if isinstance(net, dict) else ""
        coa_rows.append(
            [
                row.get("coa_id"),
                row.get("lot"),
                row.get("sku_id"),
                row.get("lab"),
                row.get("accession"),
                row.get("search_code"),
                row.get("received"),
                row.get("reported"),
                row.get("purity_percent"),
                net_text,
                row.get("file"),
                row.get("kit_photo"),
                ", ".join(row.get("associated_lot_ids") or []),
            ]
        )
    _sheet(
        wb,
        "COAs",
        [
            "coa_id",
            "lot",
            "sku_id",
            "lab",
            "accession",
            "search_code",
            "received",
            "reported",
            "purity_percent",
            "net_content_mg",
            "file",
            "kit_photo",
            "associated_lot_ids",
        ],
        coa_rows,
    )
    _sheet(
        wb,
        "Clients",
        ["name", "phone", "telegram_chat_id", "las_vegas_resident", "notes"],
        [],
    )
    wb.save(dest)
    return dest


def main() -> int:
    path = build_workbook()
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
