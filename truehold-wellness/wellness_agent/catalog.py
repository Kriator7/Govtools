"""TrueHold Wellness live shop inventory and locked information sheets."""

from __future__ import annotations

import json
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any

INVENTORY_DIR = Path(__file__).resolve().parent / "inventory"
CATALOG_PATH = INVENTORY_DIR / "catalog.json"
PDF_DIR = INVENTORY_DIR / "pdfs"
TELEGRAM_FILES_DIR = INVENTORY_DIR / "telegram_files"


class UnknownProductError(KeyError):
    """Raised when a catalog lookup does not match a live shop SKU."""


@lru_cache
def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def products() -> list[dict[str, Any]]:
    return list(load_catalog()["products"])


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("+", " plus ").split())


def find_product(query: str) -> dict[str, Any]:
    needle = _normalize(query)
    if not needle:
        raise UnknownProductError("Send /product <name>. Use /catalog for the live list.")
    exact: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []
    for item in products():
        aliases = {
            _normalize(item["id"]),
            _normalize(item["name"]),
            *(_normalize(alias) for alias in item["aliases"]),
        }
        if needle in aliases:
            exact.append(item)
        elif len(needle) >= 4 and any(
            alias.startswith(needle) or needle.startswith(alias) for alias in aliases if len(alias) >= 4
        ):
            partial.append(item)
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        names = ", ".join(item["id"] for item in exact)
        raise UnknownProductError(f"Ambiguous product {query!r} ({names}). Use /catalog.")
    if len(partial) == 1:
        return partial[0]
    raise UnknownProductError(f"No TrueHold Wellness SKU matched {query!r}. Use /catalog.")


def pdf_path(product: dict[str, Any]) -> Path:
    path = PDF_DIR / product["pdf"]
    if not path.is_file():
        raise FileNotFoundError(f"Missing locked sheet: {path.name}")
    return path


def locked_sheet_filename(product: dict[str, Any]) -> str:
    """Name shown in Telegram Files. Must not look like a shop URL."""
    return f"TrueHold Wellness locked information sheet — {product['name']}.pdf"


def telegram_file_path(product: dict[str, Any]) -> Path:
    """Agent file pack: all locked sheets in one Telegram-files directory."""
    dest = TELEGRAM_FILES_DIR / locked_sheet_filename(product)
    if dest.is_file():
        return dest
    source = pdf_path(product)
    TELEGRAM_FILES_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return dest


def sync_telegram_files() -> list[Path]:
    TELEGRAM_FILES_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for item in products():
        dest = TELEGRAM_FILES_DIR / locked_sheet_filename(item)
        shutil.copy2(pdf_path(item), dest)
        written.append(dest)
    return written


def format_catalog() -> str:
    from wellness_agent.telegram_copy import PAYMENT_COPY

    lines = [
        "TrueHold Wellness inventory",
        "Educational information only. Research use only.",
        "Tap /menu, then one name. View PDF in Telegram sends the locked sheet as a file in this chat — not a shop page.",
        "Prep and local delivery: Las Vegas residents only. Shipping: dry vials only.",
        PAYMENT_COPY,
        "",
    ]
    for item in products():
        lines.append(f"• {item['name']} — {item['vial']}")
        lines.append(f"  /product {item['id']}")
    lines.extend(
        [
            "",
            "/menu — tap a name, then View PDF in Telegram (Files, not Links)",
            "/schedule — book with the team or pay by debit card",
        ]
    )
    return "\n".join(lines) + "\n"


def format_product_caption(product: dict[str, Any]) -> str:
    """Short HTML caption for sendDocument. No http(s) URLs — Telegram Links would open the shop.

    HTML style: https://core.telegram.org/bots/api#html-style
    """
    from html import escape

    name = escape(str(product["name"]))
    vial = escape(str(product["vial"]))
    return (
        f"<b>TrueHold Wellness</b>\n"
        f"locked information sheet\n"
        f"\n"
        f"<b>{name}</b>\n"
        f"{vial}\n"
        f"\n"
        f"<b>Sheet</b>\n"
        f"Telegram file — open in Files. Not a shop page.\n"
        f"\n"
        f"<b>Prep</b>\n"
        f"Las Vegas · dry vials only · Educational only\n"
        f"\n"
        f"<b>Pay</b>\n"
        f"Zelle on the call · debit via Team"
    )
