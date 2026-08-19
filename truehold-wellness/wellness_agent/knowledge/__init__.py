"""Approved-only knowledge for the TrueHold Wellness floor team.

Runtime SQLite is gitignored. Seed JSON plus live catalog/PDF paths are the
source of truth. Customer replies may only use approved rows. Promotions are
draft until staff approve them case by case.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from wellness_agent.envfile import PACKAGE_ROOT

SEED_PATH = Path(__file__).resolve().parent / "seed.json"


def db_path() -> Path:
    override = os.environ.get("WELLNESS_KNOWLEDGE_PATH")
    if override:
        return Path(override)
    return PACKAGE_ROOT / "data" / "knowledge.sqlite"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS snippets (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            title TEXT,
            text TEXT NOT NULL,
            source TEXT,
            approved INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            path TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            headline TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at REAL NOT NULL,
            decided_at REAL,
            staff_id TEXT
        );
        """
    )
    conn.commit()


def seed_approved_knowledge() -> dict[str, int]:
    """Load seed + live SKU one-liners + PDF paths. Never copies dosing math into chat snippets."""
    from wellness_agent.catalog import locked_sheet_filename, pdf_path, products

    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    conn = connect()
    _init(conn)
    count = {"snippets": 0, "documents": 0}
    for doc in payload.get("documents") or []:
        conn.execute(
            "INSERT OR REPLACE INTO snippets(id, kind, title, text, source, approved) VALUES (?,?,?,?,?,1)",
            (doc["id"], doc.get("kind") or "policy", doc.get("title") or "", doc["text"], "seed"),
        )
        count["snippets"] += 1
    for kind, rows in (
        ("hello", payload.get("hellos") or []),
        ("joke", payload.get("jokes") or []),
        ("smalltalk", payload.get("smalltalk") or []),
        ("thanks", payload.get("thanks") or []),
    ):
        for index, text in enumerate(rows, start=1):
            conn.execute(
                "INSERT OR REPLACE INTO snippets(id, kind, title, text, source, approved) VALUES (?,?,?,?,?,1)",
                (f"{kind}-{index}", kind, kind, text, "seed"),
            )
            count["snippets"] += 1
    for item in products():
        sku_id = f"sku-{item['id']}"
        rec_text = ""
        try:
            from wellness_agent.knowledge.house import peptide_record

            rec = peptide_record(item["id"])
            rec_text = f" Opener: {rec['opener']} Prep: {rec['prep']}"
        except Exception:
            rec_text = ""
        text = (
            f"{item['name']} is a live TrueHold Wellness SKU. "
            f"Vial in stock: {item['vial']}. Dry lyophilized vial. Educational only."
            f"{rec_text} "
            "Tap the name for the tile, Sheet for the locked PDF. Mix details stay on the sheet."
        )
        conn.execute(
            "INSERT OR REPLACE INTO snippets(id, kind, title, text, source, approved) VALUES (?,?,?,?,?,1)",
            (sku_id, "product", item["name"], text, f"catalog:{item['id']}"),
        )
        count["snippets"] += 1
        pdf = str(pdf_path(item))
        conn.execute(
            "INSERT OR REPLACE INTO documents(id, title, path, approved) VALUES (?,?,?,1)",
            (item["id"], locked_sheet_filename(item), pdf),
        )
        count["documents"] += 1
    from wellness_agent.knowledge.house import seed_rows

    for row_id, kind, title, text in seed_rows():
        conn.execute(
            "INSERT OR REPLACE INTO snippets(id, kind, title, text, source, approved) VALUES (?,?,?,?,?,1)",
            (row_id, kind, title, text, "house"),
        )
        count["snippets"] += 1
    conn.commit()
    conn.close()
    return count


def approved_snippets(kind: str | None = None) -> list[dict[str, Any]]:
    conn = connect()
    _init(conn)
    if kind:
        rows = conn.execute(
            "SELECT id, kind, title, text, source FROM snippets WHERE approved=1 AND kind=? ORDER BY id",
            (kind,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, kind, title, text, source FROM snippets WHERE approved=1 ORDER BY id"
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def retrieve(query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    """Tiny approved-text search. No embeddings. Never returns unapproved rows."""
    needle = {part.lower() for part in (query or "").replace("+", " ").split() if len(part) >= 3}
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in approved_snippets():
        blob = f"{row['title']} {row['text']} {row['kind']}".lower()
        score = sum(1 for part in needle if part in blob)
        if row["kind"] == "product" and any(part in blob for part in needle):
            score += 2
        if row["kind"] == "creed":
            score += 1
            if any(
                part in needle
                for part in (
                    "nature",
                    "natural",
                    "god",
                    "vitamin",
                    "orange",
                    "oranges",
                    "truth",
                    "empower",
                    "peptide",
                    "peptides",
                    "healthy",
                    "profit",
                    "oxygen",
                    "broth",
                    "herbs",
                    "ownership",
                    "hostage",
                    "quote",
                    "emerson",
                    "paracelsus",
                    "lind",
                    "scurvy",
                    "nightingale",
                    "muir",
                    "thoreau",
                    "hippocrates",
                    "avicenna",
                    "maimonides",
                    "bacon",
                    "aristotle",
                )
            ):
                score += 2
        if row["kind"] in {"fasting", "herb", "prep", "bio", "house"}:
            score += 1
            if any(
                part in needle
                for part in (
                    "fast",
                    "fasting",
                    "herb",
                    "herbs",
                    "ginger",
                    "peppermint",
                    "chamomile",
                    "broth",
                    "bio",
                    "who",
                    "prep",
                    "sleep",
                    "window",
                    "experience",
                    "clinical",
                    "surgical",
                )
            ):
                score += 2
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [row for _, row in scored[:limit]]


def pick_snippet(kind: str, *, salt: str = "") -> str:
    rows = approved_snippets(kind)
    if not rows:
        return ""
    index = abs(hash(f"{kind}:{salt}")) % len(rows)
    return str(rows[index]["text"])


def list_promos(status: str | None = None) -> list[dict[str, Any]]:
    conn = connect()
    _init(conn)
    if status:
        rows = conn.execute(
            "SELECT id, headline, body, status, created_at, staff_id FROM promotions WHERE status=? ORDER BY id DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, headline, body, status, created_at, staff_id FROM promotions ORDER BY id DESC"
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def draft_promo(headline: str, body: str, *, staff_id: str) -> dict[str, Any]:
    conn = connect()
    _init(conn)
    cur = conn.execute(
        "INSERT INTO promotions(headline, body, status, created_at, staff_id) VALUES (?,?,?,?,?)",
        (headline.strip(), body.strip(), "pending", time.time(), staff_id),
    )
    conn.commit()
    promo_id = int(cur.lastrowid)
    conn.close()
    return {"id": promo_id, "status": "pending", "headline": headline.strip(), "body": body.strip()}


def decide_promo(promo_id: int, *, status: str, staff_id: str) -> dict[str, Any] | None:
    if status not in {"approved", "rejected", "expired"}:
        raise ValueError("status must be approved, rejected, or expired")
    conn = connect()
    _init(conn)
    row = conn.execute("SELECT id, headline, body, status FROM promotions WHERE id=?", (promo_id,)).fetchone()
    if row is None:
        conn.close()
        return None
    conn.execute(
        "UPDATE promotions SET status=?, decided_at=?, staff_id=? WHERE id=?",
        (status, time.time(), staff_id, promo_id),
    )
    conn.commit()
    conn.close()
    return {"id": promo_id, "status": status, "headline": row["headline"], "body": row["body"]}


def active_promo() -> dict[str, Any] | None:
    rows = list_promos("approved")
    return rows[0] if rows else None
