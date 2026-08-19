"""Approved attributed quotes for TrueHold Wellness chat copy.

Every posted quotation must keep author and work credit. Source URLs stay in
quotes.json for the house — never in Telegram captions.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

QUOTES_PATH = Path(__file__).resolve().parent / "quotes.json"


@lru_cache
def load_quotes() -> list[dict[str, Any]]:
    payload = json.loads(QUOTES_PATH.read_text(encoding="utf-8"))
    return list(payload.get("quotes") or [])


def quote_for_host(member_id: str) -> dict[str, Any] | None:
    for row in load_quotes():
        if str(row.get("host") or "") == str(member_id or ""):
            return row
    return None


def credited_line(row: dict[str, Any]) -> str:
    text = str(row.get("text") or "").strip()
    author = str(row.get("author") or "").strip()
    work = str(row.get("work") or "").strip()
    year = str(row.get("year") or "").strip()
    note = str(row.get("note") or "").strip()
    work_bit = f"{work} ({year})" if year else work
    line = f"“{text}” — {author}, {work_bit}"
    if note:
        line = f"{line} ({note})"
    return line


def seed_quote_rows() -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for row in load_quotes():
        quote_id = str(row.get("id") or "")
        if not quote_id:
            continue
        title = f"{row.get('author')}, {row.get('work')}".strip(", ")
        text = credited_line(row)
        rows.append((f"quote-{quote_id}", "creed", title, text))
    return rows
