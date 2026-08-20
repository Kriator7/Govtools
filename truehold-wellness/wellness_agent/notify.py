from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from wellness_agent.compose import format_alert
from wellness_agent.models import Alert
from wellness_agent.operator_store import configured_operator_chats

DEFAULT_TIMEOUT_SECONDS = 15
WEBHOOK_ENV = "WELLNESS_ALERT_WEBHOOK_URL"


class NotifyError(RuntimeError):
    """Raised when a Wellness alert could not be delivered."""


@dataclass(frozen=True)
class NotifyResult:
    delivered: bool
    dry_run: bool
    text: str
    payload: dict[str, Any]
    destination: str | None = None
    status: str = "ok"


def alert_payload(alert: Alert) -> dict[str, Any]:
    """JSON body posted when a Wellness alert fires. Always includes the full inbox snapshot."""
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
    exclude_chats: set[str] | None = None,
    require_destination: bool = True,
) -> NotifyResult:
    """
    Send a TrueHold Wellness alert.

    Uses WELLNESS_ALERT_WEBHOOK_URL (not the crypto ALERT_WEBHOOK_URL).
    Also delivers the same text to @THWellness_bot when TELEGRAM_MODE=live.
    """
    payload = alert_payload(alert)
    text = payload["text"]
    destination = webhook_url or os.environ.get(WEBHOOK_ENV)
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_live = os.environ.get("TELEGRAM_MODE", "mock") == "live"
    skip = {str(item) for item in (exclude_chats or set())}
    operator_chats = [chat_id for chat_id in configured_operator_chats() if chat_id not in skip]
    if dry_run:
        return NotifyResult(
            delivered=False,
            dry_run=True,
            text=text,
            payload=payload,
            destination=destination,
            status="dry_run",
        )
    destinations: list[str] = []
    if destination:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            destination,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "truehold-wellness-agent/0.1",
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
        destinations.append(destination)
    if telegram_live and telegram_token and operator_chats:
        from wellness_agent.telegram_api import WellnessTelegram

        client = WellnessTelegram(telegram_token)
        client.assert_identity()
        for chat_id in operator_chats:
            client.send_message(chat_id, text)
        destinations.append("telegram:@THWellness_bot")
    if not destinations:
        if not require_destination:
            return NotifyResult(
                delivered=False,
                dry_run=False,
                text=text,
                payload=payload,
                destination=None,
                status="queued_no_destination",
            )
        raise NotifyError(
            f"No {WEBHOOK_ENV} configured and live @THWellness_bot chat is not set. "
            "Pass webhook_url, set WELLNESS_ALERT_WEBHOOK_URL, or /start on @THWellness_bot "
            "so WELLNESS_TELEGRAM_CHAT_ID / operator.json is set."
        )
    return NotifyResult(
        delivered=True,
        dry_run=False,
        text=text,
        payload=payload,
        destination=",".join(destinations),
        status="sent",
    )
