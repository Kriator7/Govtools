"""Structured tool results. A success flag is set only by the caller after checks."""

from __future__ import annotations

from typing import Any

from jarvis.clock import TZ_NAME, iso

STATUSES = (
    "CONNECTED",
    "DISCONNECTED",
    "PENDING AUTHORIZATION",
    "FAILED",
)


def envelope(
    tool: str,
    *,
    ok: bool,
    execution_status: str,
    data: dict[str, Any] | None = None,
    error: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "status": "success" if ok else "error",
        "tool": tool,
        "execution_status": execution_status,
        "timestamp": iso(),
        "timezone": TZ_NAME,
        "data": data or {},
        "error": error,
    }


def success(tool: str, data: dict[str, Any], execution_status: str = "completed") -> dict[str, Any]:
    return envelope(tool, ok=True, execution_status=execution_status, data=data, error=None)


def failure(
    tool: str,
    code: str,
    message: str,
    action: str,
    *,
    execution_status: str = "failed",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return envelope(
        tool,
        ok=False,
        execution_status=execution_status,
        data=data,
        error={"code": code, "message": message, "action": action},
    )
