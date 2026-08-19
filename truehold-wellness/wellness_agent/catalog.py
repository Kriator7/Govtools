"""TrueHold Wellness live shop inventory and locked information sheets."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

INVENTORY_DIR = Path(__file__).resolve().parent / "inventory"
CATALOG_PATH = INVENTORY_DIR / "catalog.json"
PDF_DIR = INVENTORY_DIR / "pdfs"


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


def format_catalog() -> str:
    from wellness_agent.telegram_copy import PAYMENT_COPY, SHOP_URL

    lines = [
        "TrueHold Wellness inventory",
        "Educational information only. Research use only.",
        "Tap /menu, then one name. View the PDF in Telegram — tap to open or download.",
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
            "/menu — tap a name, then View PDF in Telegram",
            "/schedule — book with the team",
            f"Debit-card checkout: {SHOP_URL}",
        ]
    )
    return "\n".join(lines) + "\n"


def format_product_caption(product: dict[str, Any]) -> str:
    from wellness_agent.telegram_copy import PAYMENT_COPY

    return (
        f"TrueHold Wellness information sheet — {product['name']}\n"
        f"{product['vial']}\n"
        "This PDF opens in Telegram. Tap it to view, or download it to save.\n"
        "Educational only. Dry (lyophilized) vial. Protocol details reviewed case by case.\n"
        "Prep and local delivery: Las Vegas residents only.\n"
        f"{PAYMENT_COPY}"
    )
