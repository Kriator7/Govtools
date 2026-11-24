"""Local operator interface. Binds to loopback. Internal runs require a bearer token."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jarvis.cron import next_after
from jarvis.clock import now
from jarvis.mcp_server import handle as mcp_handle
from jarvis.probes import cached_probes, ensure_qdrant_collections
from jarvis.tools import TOOLS, call

STATIC = Path(__file__).resolve().parent / "static" / "index.html"


def make_handler(ctx: Any):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return None

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                body = STATIC.read_bytes()
                self._send(200, body, "text/html; charset=utf-8")
                return
            if path == "/api/status":
                self._json(200, _status(ctx))
                return
            if path == "/api/tools":
                self._json(200, {"tools": [{"name": name, "description": spec["description"]} for name, spec in TOOLS.items()]})
                return
            if path == "/api/tasks":
                self._json(200, call(ctx, "list_tasks", {"include_cancelled": True}))
                return
            if path == "/api/upcoming":
                self._json(200, _upcoming(ctx))
                return
            if path == "/api/executions":
                self._json(200, call(ctx, "get_execution_logs", {"limit": 50}))
                return
            if path == "/api/failures":
                self._json(200, call(ctx, "get_execution_logs", {"limit": 50, "failed_only": True}))
                return
            if path == "/api/memory":
                self._json(200, _memory(ctx))
                return
            if path == "/api/approvals":
                self._json(200, {"approvals": [] if ctx.store is None else ctx.store.list_approvals()})
                return
            if path == "/api/notifications":
                self._json(200, {"notifications": [] if ctx.store is None else ctx.store.list_notifications()})
                return
            self._json(404, {"ok": False, "error": {"message": "not found", "action": "Use the operator page."}})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            payload = self._payload()
            if path == "/api/internal/run":
                if not _bearer_ok(self, ctx):
                    self._json(401, {"ok": False, "error": {"code": "unauthorized", "message": "Bearer token required.", "action": "Send the gateway token."}})
                    return
                self._json(200, call(ctx, str(payload.get("tool") or ""), payload.get("arguments") or {}))
                return
            if path == "/mcp":
                if not _bearer_ok(self, ctx):
                    self._json(401, {"ok": False, "error": {"code": "unauthorized", "message": "MCP bearer token required.", "action": "Authorize the MCP client with the gateway token."}})
                    return
                response = mcp_handle(payload, ctx)
                self._json(200, response or {})
                return
            if path == "/api/tasks":
                self._json(200, call(ctx, "schedule_task", payload))
                return
            if path.startswith("/api/tasks/") and path.endswith("/run"):
                task_id = path.split("/")[3]
                self._json(200, call(ctx, "run_task_now", {"task_id": task_id}))
                return
            if path.startswith("/api/tasks/") and path.endswith("/pause"):
                task_id = path.split("/")[3]
                self._json(200, call(ctx, "pause_task", {"task_id": task_id}))
                return
            if path.startswith("/api/tasks/") and path.endswith("/resume"):
                task_id = path.split("/")[3]
                self._json(200, call(ctx, "resume_task", {"task_id": task_id}))
                return
            if path == "/api/memory":
                self._json(200, call(ctx, "remember_information", payload))
                return
            if path.startswith("/api/approvals/") and path.endswith("/decide"):
                approval_id = path.split("/")[3]
                self._json(200, _decide(ctx, approval_id, str(payload.get("status") or "")))
                return
            if path == "/api/tools/call":
                self._json(200, call(ctx, str(payload.get("tool") or ""), payload.get("arguments") or {}))
                return
            self._json(404, {"ok": False})

        def do_PATCH(self) -> None:
            path = urlparse(self.path).path
            payload = self._payload()
            if path.startswith("/api/tasks/"):
                task_id = path.split("/")[3]
                payload["task_id"] = task_id
                self._json(200, call(ctx, "update_task", payload))
                return
            if path.startswith("/api/memory/"):
                memory_id = path.split("/")[3]
                payload["memory_id"] = memory_id
                self._json(200, call(ctx, "update_memory", payload))
                return
            self._json(404, {"ok": False})

        def _payload(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(min(length, 1_000_000))
            try:
                body = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return {}
            return body if isinstance(body, dict) else {}

        def _json(self, status: int, body: Any) -> None:
            data = json.dumps(body).encode("utf-8")
            self._send(status, data, "application/json")

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _bearer_ok(handler: BaseHTTPRequestHandler, ctx: Any) -> bool:
    expected = ctx.credentials.get("JARVIS_GATEWAY_TOKEN")
    header = handler.headers.get("Authorization") or ""
    if not expected or not header.startswith("Bearer "):
        return False
    return header.removeprefix("Bearer ").strip() == expected


def _status(ctx: Any) -> dict[str, Any]:
    try:
        ensure_qdrant_collections(ctx)
    except Exception:
        pass
    ctx._probe_cache = None
    rows = cached_probes(ctx)
    return {
        "timezone": "America/Los_Angeles",
        "store_backend": None if ctx.store is None else ctx.store.backend,
        "store_error": ctx.store_error,
        "integrations": rows,
        "mcp_auth": "bearer",
    }


def _upcoming(ctx: Any) -> dict[str, Any]:
    if ctx.store is None:
        return {"upcoming": [], "error": ctx.store_error}
    rows = []
    for task in ctx.store.list_tasks(include_cancelled=False):
        if task.get("enabled") and task.get("cron"):
            moment = next_after(task["cron"], now())
            rows.append({"task_id": task["id"], "name": task["name"], "next_run": moment.isoformat(timespec="seconds")})
    rows.sort(key=lambda item: item["next_run"])
    return {"upcoming": rows}


def _memory(ctx: Any) -> dict[str, Any]:
    if ctx.store is None:
        return {"memories": [], "error": ctx.store_error}
    personal = ctx.store.search_memories("", ["personal"])
    business = ctx.store.search_memories("", ["business"])
    return {"personal": personal, "business": business, "confidential_hidden": True}


def _decide(ctx: Any, approval_id: str, status: str) -> dict[str, Any]:
    if status not in {"approved", "rejected"}:
        return {"ok": False, "error": {"code": "invalid_decision", "message": "Decision must be approved or rejected.", "action": "Choose one."}}
    if ctx.store is None:
        return {"ok": False, "error": {"message": ctx.store_error, "action": "Restore PostgreSQL."}}
    row = ctx.store.decide_approval(approval_id, status)
    if row is None:
        return {"ok": False, "error": {"code": "not_found", "message": "No approval has that id.", "action": "Refresh approvals."}}
    return {"ok": True, "approval": row, "schedule_enabled": False}


def serve(ctx: Any, host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    ctx.mcp_listening = True
    server = ThreadingHTTPServer((host, port), make_handler(ctx))
    return server
