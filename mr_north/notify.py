from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from mr_north.compose import format_alert
from mr_north.models import AGENT_ID, Alert

DEFAULT_TIMEOUT_SECONDS = 15


class NotifyError(RuntimeError):
    """Raised when an Mr North alert could not be delivered."""


@dataclass(frozen=True)
class NotifyResult:
    delivered: bool
    dry_run: bool
    text: str
    payload: dict[str, Any]
    destination: str | None = None
    status: str = "ok"


def alert_payload(alert: Alert) -> dict[str, Any]:
    """JSON body posted when Mr North fires an alert. Always includes the catalyst briefing."""
    return {
        **alert.to_dict(),
        "text": format_alert(alert),
    }


def send_alert(
    alert: Alert,
    *,
    webhook_url: str | None = None,
    dry_run: bool = False,
    opener: Callable[..., Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> NotifyResult:
    """
    Send an Mr North alert.

    When dry_run is true, the payload is returned without network I/O.
    Otherwise the agent POSTs JSON (including catalyst data) to ALERT_WEBHOOK_URL
    or the explicit webhook_url argument.
    """
    payload = alert_payload(alert)
    text = payload["text"]
    destination = webhook_url or os.environ.get("ALERT_WEBHOOK_URL")
    if dry_run:
        return NotifyResult(
            delivered=False,
            dry_run=True,
            text=text,
            payload=payload,
            destination=destination,
            status="dry_run",
        )
    if not destination:
        raise NotifyError(
            "No ALERT_WEBHOOK_URL configured. Pass webhook_url or set the environment variable."
        )
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        destination,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"{AGENT_ID}/0.1",
        },
    )
    post = opener or urllib.request.urlopen
    try:
        with post(request, timeout=timeout) as response:
            status_code = getattr(response, "status", 200)
            if status_code >= 400:
                raise NotifyError(f"Webhook returned HTTP {status_code}")
    except urllib.error.URLError as exc:
        raise NotifyError(f"Webhook delivery failed: {exc}") from exc
    return NotifyResult(
        delivered=True,
        dry_run=False,
        text=text,
        payload=payload,
        destination=destination,
        status="sent",
    )
