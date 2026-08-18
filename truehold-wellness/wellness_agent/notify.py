from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from wellness_agent.compose import format_alert
from wellness_agent.models import Alert

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
) -> NotifyResult:
    """
    Send a TrueHold Wellness alert.

    Uses WELLNESS_ALERT_WEBHOOK_URL (not the crypto ALERT_WEBHOOK_URL).
    Also delivers the same text to @Npeppers_bot when TELEGRAM_MODE=live.
    """
    payload = alert_payload(alert)
    text = payload["text"]
    destination = webhook_url or os.environ.get(WEBHOOK_ENV)
    telegram_chat = os.environ.get("WELLNESS_TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_OPERATOR_CHAT_ID")
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_live = os.environ.get("TELEGRAM_MODE", "mock") == "live"
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
    if telegram_live and telegram_token and telegram_chat:
        from wellness_agent.telegram_api import WellnessTelegram

        client = WellnessTelegram(telegram_token)
        client.assert_identity()
        client.send_message(telegram_chat, text)
        destinations.append(f"telegram:@Npeppers_bot")
    if not destinations:
        raise NotifyError(
            f"No {WEBHOOK_ENV} configured and live @Npeppers_bot chat is not set. "
            "Pass webhook_url, set WELLNESS_ALERT_WEBHOOK_URL, or set TELEGRAM_MODE=live "
            "with TELEGRAM_BOT_TOKEN and WELLNESS_TELEGRAM_CHAT_ID."
        )
    return NotifyResult(
        delivered=True,
        dry_run=False,
        text=text,
        payload=payload,
        destination=",".join(destinations),
        status="sent",
    )
