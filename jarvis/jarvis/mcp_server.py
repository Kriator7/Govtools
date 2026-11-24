"""Minimal MCP JSON-RPC. HTTP calls require the gateway bearer token."""

from __future__ import annotations

import json
from typing import Any

from jarvis import __version__
from jarvis.tools import TOOLS, call


def handle(message: dict[str, Any], ctx: Any) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _ok(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "jarvis-mark-vii", "version": __version__},
            },
        )
    if method == "tools/list":
        return _ok(
            request_id,
            {
                "tools": [
                    {"name": name, "description": spec["description"], "inputSchema": spec["schema"]}
                    for name, spec in TOOLS.items()
                ]
            },
        )
    if method == "tools/call":
        params = message.get("params") or {}
        result = call(ctx, str(params.get("name") or ""), params.get("arguments") or {})
        return _ok(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(result)}],
                "isError": not bool(result.get("ok")),
            },
        )
    return _err(request_id, -32601, "method not found")


def _ok(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def stdio_main(ctx: Any) -> None:
    import sys

    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue
        try:
            message = json.loads(text)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(_err(None, -32700, "parse error")) + "\n")
            sys.stdout.flush()
            continue
        response = handle(message, ctx)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
