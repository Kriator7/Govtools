"""Runtime dependencies for tools. Secrets stay on the credential store."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from jarvis.credentials import CredentialStore
from jarvis.http_util import read_text, request_json
from jarvis.store import MemoryStore, PostgresStore, postgres_dsn


Fetch = Callable[..., tuple[int, Any]]


def default_fetch(method: str, url: str, payload: Any = None, headers: dict[str, str] | None = None, timeout: float = 8, public_only: bool = False):
    return request_json(method, url, payload, headers, timeout, public_only=public_only)


@dataclass
class Context:
    store: Any
    credentials: CredentialStore
    repo_root: Path
    fetch: Fetch = default_fetch
    read_url: Callable[[str], str] = read_text
    approved_root: Path | None = None
    store_error: str | None = None
    mcp_listening: bool = False
    overrides: dict[str, str] = field(default_factory=dict)

    def approved_dir(self) -> Path:
        root = self.approved_root or (self.repo_root / "jarvis" / "var" / "approved")
        root.mkdir(parents=True, exist_ok=True)
        return root


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[2]


def open_context(
    *,
    repo_root: Path | None = None,
    credentials: CredentialStore | None = None,
    store: Any = None,
    fetch: Fetch | None = None,
    approved_root: Path | None = None,
) -> Context:
    creds = credentials or CredentialStore.load()
    root = repo_root or repo_root_from_here()
    store_error = None
    if store is None:
        mode = os.environ.get("JARVIS_STORE", "auto")
        if mode == "memory":
            store = MemoryStore()
            store.migrate()
            store.seed_automations()
        else:
            password = creds.get("POSTGRES_PASSWORD")
            if not password:
                store_error = "POSTGRES_PASSWORD is missing from the credential file. Refusing an in-memory fallback."
                store = None
            else:
                dsn = postgres_dsn(
                    os.environ.get("POSTGRES_USER", "jarvis"),
                    password,
                    os.environ.get("POSTGRES_HOST", "127.0.0.1"),
                    os.environ.get("POSTGRES_PORT", "5432"),
                    os.environ.get("POSTGRES_DB", "jarvis"),
                )
                try:
                    store = PostgresStore(dsn)
                    store.migrate()
                    store.seed_automations()
                except Exception as exc:
                    store_error = f"PostgreSQL is not usable: {exc.__class__.__name__}"
                    store = None
    return Context(
        store=store,
        credentials=creds,
        repo_root=root,
        fetch=fetch or default_fetch,
        approved_root=approved_root,
        store_error=store_error,
    )
