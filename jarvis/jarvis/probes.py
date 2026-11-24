"""Live integration probes. Status is the result of a check, not a stored label."""

from __future__ import annotations

import shutil
from typing import Any

from jarvis.clock import iso
from jarvis.http_util import HttpError

QDRANT_COLLECTIONS = ("personal", "business", "confidential")


def _row(integration_id: str, name: str, status: str, detail: str, action: str = "") -> dict[str, str]:
    return {
        "id": integration_id,
        "name": name,
        "status": status,
        "detail": detail,
        "action": action,
        "checked_at": iso(),
    }


def _get(ctx: Any, url: str, headers: dict[str, str] | None = None, timeout: float = 3, public_only: bool = False):
    return ctx.fetch("GET", url, None, headers, timeout, public_only)


def cached_probes(ctx: Any) -> list[dict[str, str]]:
    import time

    stamp = time.monotonic()
    cached = getattr(ctx, "_probe_cache", None)
    if cached and not ctx.overrides and stamp - cached[0] < 5:
        return cached[1]
    rows = probe_all(ctx)
    ctx._probe_cache = (stamp, rows)
    return rows


def probe_all(ctx: Any) -> list[dict[str, str]]:
    if ctx.overrides:
        rows = []
        for key, status in ctx.overrides.items():
            rows.append(_row(key, key, status, "test override", ""))
        return rows
    return [
        probe_postgres(ctx),
        probe_qdrant(ctx),
        probe_n8n(ctx, "n8n_house", "House n8n", ctx.credentials.get("N8N_URL") or "http://127.0.0.1:15678"),
        probe_n8n(ctx, "n8n_lab", "Lab n8n", ctx.credentials.get("N8N_LAB_URL") or "http://127.0.0.1:15680"),
        probe_n8n_api(ctx),
        probe_ollama(ctx),
        probe_embeddings(ctx),
        probe_voice(ctx),
        probe_email(ctx),
        probe_calendar(ctx),
        probe_market(ctx),
        probe_cardano_node(ctx),
        probe_cardano_releases(ctx),
        probe_business_ledger(ctx),
        probe_notification(ctx),
        probe_mcp(ctx),
        probe_catalog(ctx),
    ]


def probe_postgres(ctx: Any) -> dict[str, str]:
    if ctx.store_error:
        return _row("postgres", "PostgreSQL", "FAILED", ctx.store_error, "Start PostgreSQL and set POSTGRES_PASSWORD in the credential file.")
    if ctx.store is None or ctx.store.backend != "postgres":
        return _row(
            "postgres",
            "PostgreSQL",
            "DISCONNECTED",
            "This process is not using PostgreSQL.",
            "Set JARVIS_STORE=auto and provide POSTGRES_PASSWORD.",
        )
    try:
        ctx.store.list_tasks()
    except Exception as exc:
        return _row("postgres", "PostgreSQL", "FAILED", exc.__class__.__name__, "Check that the jarvis database accepts logins on 127.0.0.1:5432.")
    return _row("postgres", "PostgreSQL", "CONNECTED", "SELECT against tasks succeeded.", "")


def probe_qdrant(ctx: Any) -> dict[str, str]:
    base = ctx.credentials.get("QDRANT_URL") or "http://127.0.0.1:6333"
    try:
        status, body = _get(ctx, f"{base}/collections", timeout=3)
    except Exception as exc:
        return _row("qdrant", "Qdrant", "DISCONNECTED", exc.__class__.__name__, "Start Qdrant and set QDRANT_URL if it is not on 127.0.0.1:6333.")
    if status != 200 or not isinstance(body, dict):
        return _row("qdrant", "Qdrant", "FAILED", f"HTTP {status}", "Check the Qdrant process logs.")
    names = set()
    for item in (body.get("result") or {}).get("collections") or []:
        if isinstance(item, dict) and item.get("name"):
            names.add(item["name"])
    missing = [name for name in QDRANT_COLLECTIONS if name not in names]
    if missing:
        return _row(
            "qdrant",
            "Qdrant",
            "FAILED",
            "Missing collections: " + ", ".join(missing),
            "Run jarvis ensure-qdrant to create personal, business, and confidential.",
        )
    return _row("qdrant", "Qdrant", "CONNECTED", "personal, business, and confidential collections exist.", "")


def ensure_qdrant_collections(ctx: Any) -> dict[str, Any]:
    base = ctx.credentials.get("QDRANT_URL") or "http://127.0.0.1:6333"
    created: list[str] = []
    for name in QDRANT_COLLECTIONS:
        status, _body = ctx.fetch(
            "PUT",
            f"{base}/collections/{name}",
            {"vectors": {"size": 384, "distance": "Cosine"}},
            None,
            5,
            False,
        )
        if status in {200, 201, 409}:
            created.append(name)
        else:
            raise HttpError(f"Qdrant refused collection {name} with HTTP {status}", status)
    return {"collections": created, "semantic_embeddings": False}


def probe_n8n(ctx: Any, integration_id: str, name: str, base: str) -> dict[str, str]:
    try:
        status, body = _get(ctx, f"{base.rstrip('/')}/healthz", timeout=2)
    except Exception:
        return _row(integration_id, name, "DISCONNECTED", f"No response from {base}/healthz", "Start that n8n instance or set its URL in the credential file.")
    if status == 200:
        return _row(integration_id, name, "CONNECTED", f"healthz returned 200 at {base}.", "")
    return _row(integration_id, name, "FAILED", f"HTTP {status}", "Read the n8n container logs.")


def probe_n8n_api(ctx: Any) -> dict[str, str]:
    key = ctx.credentials.get("N8N_API_KEY")
    base = _preferred_n8n(ctx)
    if base is None:
        return _row("n8n_api", "n8n API", "DISCONNECTED", "No n8n healthz responded.", "Start house n8n or the lab instance.")
    if not key:
        return _row(
            "n8n_api",
            "n8n API",
            "PENDING AUTHORIZATION",
            f"{base} is up and no API key is stored.",
            "Create an n8n API key in the credential file as N8N_API_KEY. Do not paste it into chat.",
        )
    try:
        status, _body = _get(ctx, f"{base}/api/v1/workflows?limit=1", headers={"X-N8N-API-KEY": key}, timeout=4)
    except Exception as exc:
        return _row("n8n_api", "n8n API", "FAILED", exc.__class__.__name__, "Confirm the API key belongs to this n8n instance.")
    if status == 200:
        return _row("n8n_api", "n8n API", "CONNECTED", f"Workflow list succeeded at {base}.", "")
    if status in {401, 403}:
        return _row("n8n_api", "n8n API", "PENDING AUTHORIZATION", f"HTTP {status}", "Replace N8N_API_KEY with a key from this instance.")
    return _row("n8n_api", "n8n API", "FAILED", f"HTTP {status}", "Check n8n public API access.")


def _preferred_n8n(ctx: Any) -> str | None:
    for base in (
        ctx.credentials.get("N8N_URL") or "http://127.0.0.1:15678",
        ctx.credentials.get("N8N_LAB_URL") or "http://127.0.0.1:15680",
    ):
        try:
            status, _body = _get(ctx, f"{base.rstrip('/')}/healthz", timeout=2)
        except Exception:
            continue
        if status == 200:
            return base.rstrip("/")
    return None


def preferred_n8n_base(ctx: Any) -> str | None:
    return _preferred_n8n(ctx)


def probe_ollama(ctx: Any) -> dict[str, str]:
    base = (ctx.credentials.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
    try:
        status, body = _get(ctx, f"{base}/api/tags", timeout=2)
    except Exception:
        return _row(
            "ollama",
            "Ollama",
            "DISCONNECTED",
            "Tags endpoint did not respond. The existing install was not modified.",
            "Start the existing Ollama service. JARVIS will not pull or replace a model.",
        )
    if status != 200:
        return _row("ollama", "Ollama", "FAILED", f"HTTP {status}", "Inspect the existing Ollama service.")
    models = []
    if isinstance(body, dict):
        models = [item.get("name") for item in body.get("models") or [] if isinstance(item, dict)]
    return _row("ollama", "Ollama", "CONNECTED", "Models visible: " + (", ".join(models) if models else "none"), "")


def probe_embeddings(ctx: Any) -> dict[str, str]:
    return _row(
        "embeddings",
        "Semantic embeddings",
        "DISCONNECTED",
        "Embedding calls are not part of the health probe, so the resident Ollama model is left loaded as-is.",
        "Lexical memory search is active. Do not treat Qdrant as semantic until an embedding check is run on purpose.",
    )


def probe_voice(ctx: Any) -> dict[str, str]:
    url = ctx.credentials.get("JARVIS_VOICE_HEALTH_URL")
    if not url:
        return _row(
            "voice",
            "Voice",
            "DISCONNECTED",
            "No voice health URL is configured. The existing voice system was not modified.",
            "Set JARVIS_VOICE_HEALTH_URL only if you want JARVIS to probe voice. JARVIS does not start or replace it.",
        )
    try:
        status, _body = _get(ctx, url, timeout=2)
    except Exception:
        return _row("voice", "Voice", "DISCONNECTED", "The configured voice health URL did not respond.", "Check the existing voice process.")
    if status == 200:
        return _row("voice", "Voice", "CONNECTED", "Health URL returned 200.", "")
    return _row("voice", "Voice", "FAILED", f"HTTP {status}", "Read the voice service log.")


def probe_email(ctx: Any) -> dict[str, str]:
    if not (ctx.credentials.present("IMAP_USER") and ctx.credentials.present("IMAP_PASSWORD")):
        return _row(
            "email",
            "Email",
            "PENDING AUTHORIZATION",
            "IMAP credentials are not in the credential file.",
            "Store an app password in the n8n IMAP credential or in IMAP_USER and IMAP_PASSWORD. Do not paste it into chat.",
        )
    return _row(
        "email",
        "Email",
        "PENDING AUTHORIZATION",
        "Credentials are present but a mailbox login has not been verified by this probe.",
        "Run the email tool once so the login result can be recorded. A present password is not a connection.",
    )


def probe_calendar(ctx: Any) -> dict[str, str]:
    if not ctx.credentials.present("GOOGLE_CALENDAR_ACCESS_TOKEN"):
        return _row(
            "calendar",
            "Calendar",
            "PENDING AUTHORIZATION",
            "No Google Calendar access token is stored.",
            "Authorize calendar access and store the token outside the model context.",
        )
    token = ctx.credentials.get("GOOGLE_CALENDAR_ACCESS_TOKEN")
    try:
        status, _body = _get(
            ctx,
            "https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
            public_only=True,
        )
    except Exception as exc:
        return _row("calendar", "Calendar", "FAILED", exc.__class__.__name__, "Retry the calendar list call.")
    if status == 200:
        return _row("calendar", "Calendar", "CONNECTED", "calendarList returned 200.", "")
    if status in {401, 403}:
        return _row("calendar", "Calendar", "PENDING AUTHORIZATION", f"HTTP {status}", "Renew the calendar token.")
    return _row("calendar", "Calendar", "FAILED", f"HTTP {status}", "Read the Calendar API error.")


def probe_market(ctx: Any) -> dict[str, str]:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_last_updated_at=true"
    try:
        status, body = _get(ctx, url, timeout=6, public_only=True)
    except Exception as exc:
        return _row("market", "Market data", "DISCONNECTED", exc.__class__.__name__, "Retry the CoinGecko simple price call.")
    if status == 200 and isinstance(body, dict) and "bitcoin" in body:
        return _row("market", "Market data", "CONNECTED", "CoinGecko returned a bitcoin price.", "")
    return _row("market", "Market data", "FAILED", f"HTTP {status}", "Retry later. Keyless CoinGecko is rate limited.")


def probe_cardano_node(ctx: Any) -> dict[str, str]:
    url = ctx.credentials.get("CARDANO_NODE_HEALTH_URL")
    if not url:
        return _row(
            "cardano_node",
            "Cardano node",
            "DISCONNECTED",
            "No read-only health URL is configured. Keys were not read.",
            "Set CARDANO_NODE_HEALTH_URL to a read-only status document. An unreachable monitor is not a node failure.",
        )
    try:
        status, body = _get(ctx, url, timeout=4)
    except Exception as exc:
        return _row("cardano_node", "Cardano node", "DISCONNECTED", exc.__class__.__name__, "Restore the health endpoint. Do not treat this as a proven node fault.")
    if status != 200 or not isinstance(body, dict):
        return _row("cardano_node", "Cardano node", "FAILED", f"HTTP {status}", "The health endpoint responded without a JSON status document.")
    return _row("cardano_node", "Cardano node", "CONNECTED", "Health document retrieved.", "")


def probe_cardano_releases(ctx: Any) -> dict[str, str]:
    url = "https://api.github.com/repos/IntersectMBO/cardano-node/releases/latest"
    try:
        status, body = _get(ctx, url, timeout=6, public_only=True)
    except Exception as exc:
        return _row("cardano_releases", "Cardano releases", "DISCONNECTED", exc.__class__.__name__, "Retry the GitHub releases request.")
    if status == 200 and isinstance(body, dict) and body.get("tag_name"):
        return _row("cardano_releases", "Cardano releases", "CONNECTED", f"Latest tag {body['tag_name']}.", "")
    return _row("cardano_releases", "Cardano releases", "FAILED", f"HTTP {status}", "Retry the IntersectMBO/cardano-node releases request.")


def probe_business_ledger(ctx: Any) -> dict[str, str]:
    if not ctx.credentials.present("JARVIS_CLIENT_LEDGER"):
        return _row(
            "business_ledger",
            "Business ledger",
            "DISCONNECTED",
            "No client ledger file is configured. Sample catalogs are not a ledger.",
            "Set JARVIS_CLIENT_LEDGER to an approved JSON ledger.",
        )
    return _row("business_ledger", "Business ledger", "PENDING AUTHORIZATION", "A path is set but this probe does not open it.", "Run search_clients to verify the file.")


def probe_notification(ctx: Any) -> dict[str, str]:
    if ctx.store is not None and ctx.store.verified_notification():
        return _row("notification_channel", "Notifications", "CONNECTED", "A notification was delivered and the response was recorded.", "")
    if not ctx.credentials.present("JARVIS_NOTIFY_WEBHOOK"):
        return _row(
            "notification_channel",
            "Notifications",
            "PENDING AUTHORIZATION",
            "No notification webhook is configured.",
            "Set JARVIS_NOTIFY_WEBHOOK. Delivery is not claimed until a 2xx response is stored.",
        )
    return _row(
        "notification_channel",
        "Notifications",
        "PENDING AUTHORIZATION",
        "A webhook is configured and no delivery has succeeded.",
        "Send a test notification and require HTTP 2xx before enabling schedules.",
    )


def probe_mcp(ctx: Any) -> dict[str, str]:
    if ctx.mcp_listening:
        return _row("mcp", "JARVIS MCP", "CONNECTED", "This HTTP process is serving /mcp and requires a bearer token.", "")
    return _row("mcp", "JARVIS MCP", "DISCONNECTED", "The MCP HTTP listener is not this process.", "Start jarvis serve and call /mcp with the gateway token.")


def probe_catalog(ctx: Any) -> dict[str, str]:
    path = ctx.repo_root / "truehold-wellness" / "wellness_agent" / "inventory" / "catalog.json"
    if path.is_file():
        return _row("catalog", "Wellness catalog", "CONNECTED", f"Read {path.name}. Counts in this file are not live stock.", "")
    return _row("catalog", "Wellness catalog", "DISCONNECTED", "catalog.json is missing.", "Restore the TrueHold Wellness catalog.")


def runtime_resources() -> dict[str, Any]:
    usage = shutil.disk_usage("/")
    return {
        "scope": "jarvis_runtime",
        "disk_total_bytes": usage.total,
        "disk_used_bytes": usage.used,
        "disk_free_bytes": usage.free,
    }
