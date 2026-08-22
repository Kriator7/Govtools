from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from mr_north.compose import format_alert
from mr_north.identity import WrongTelegramBotError
from mr_north.models import AGENT_ID, Alert
from mr_north.telegram import (
    CHAT_ENV,
    FORBIDDEN_CHAT_IDS,
    GROUP_ENV,
    NORTH_GROUP_TITLE,
    TOKEN_ENV,
    TelegramError,
    configured_chat_ids,
    configured_token,
    live_client,
    north_group_chat_id,
    save_group_chat_id,
)

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


def _post_webhook(
    destination: str,
    payload: dict[str, Any],
    *,
    opener: Callable[..., Any] | None,
    timeout: int,
) -> None:
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


def send_alert(
    alert: Alert,
    *,
    webhook_url: str | None = None,
    dry_run: bool = False,
    opener: Callable[..., Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    telegram_opener: Callable[..., Any] | None = None,
) -> NotifyResult:
    """
    Send an Mr North alert to every configured Telegram chat.

    Primary: Telegram sendMessage on North's own bot
    (`NORTH_TELEGRAM_BOT_TOKEN` + `NORTH_TELEGRAM_CHAT_ID` and
    `NORTH_TELEGRAM_GROUP_CHAT_ID`). Hourly BLS, the larger catalyst
    briefing, and immediate market watches all fan out to both locations.
    Optional extra: POST JSON to ALERT_WEBHOOK_URL.

    Never reads Wellness TELEGRAM_BOT_TOKEN or the realtor token.
    """
    payload = alert_payload(alert)
    text = payload["text"]
    webhook = webhook_url or os.environ.get("ALERT_WEBHOOK_URL")
    token = configured_token()
    chat_ids = configured_chat_ids()
    required_group = north_group_chat_id()
    if dry_run:
        dest = []
        if token and chat_ids:
            dest.append("telegram:" + ",".join(chat_ids))
        if webhook:
            dest.append(webhook)
        return NotifyResult(
            delivered=False,
            dry_run=True,
            text=text,
            payload=payload,
            destination=",".join(dest) or None,
            status="dry_run",
        )
    destinations: list[str] = []
    if token and chat_ids:
        try:
            client = live_client(opener=telegram_opener)
            username = client.assert_identity()
        except (TelegramError, WrongTelegramBotError) as exc:
            raise NotifyError(str(exc)) from exc
        sent: list[str] = []
        errors: list[str] = []
        resolver = getattr(client, "resolve_group_chat_id", None)
        if callable(resolver):
            try:
                resolved = str(resolver(required_group) or "").strip()
            except TelegramError:
                resolved = ""
            if resolved and resolved not in FORBIDDEN_CHAT_IDS:
                chat_ids = [item for item in chat_ids if item != required_group]
                if resolved not in chat_ids:
                    chat_ids.append(resolved)
                required_group = resolved
            elif required_group:
                wrong_title = getattr(client, "group_id_is_wrong_title", None)
                if callable(wrong_title) and wrong_title(required_group):
                    chat_ids = [item for item in chat_ids if item != required_group]
        for chat_id in chat_ids:
            try:
                client.send_report(chat_id, text)
            except TelegramError as exc:
                errors.append(f"{chat_id}: {exc}")
                continue
            sent.append(chat_id)
        if required_group and required_group not in sent:
            discover = getattr(client, "discover_north_group", None)
            recovered = ""
            if callable(discover):
                try:
                    recovered = str(discover(timeout=0) or "").strip()
                except TelegramError:
                    recovered = ""
            if recovered and recovered not in FORBIDDEN_CHAT_IDS and recovered not in sent:
                try:
                    client.send_report(recovered, text)
                    sent.append(recovered)
                    save_group_chat_id(recovered)
                    required_group = recovered
                except TelegramError as exc:
                    errors.append(f"{recovered}: {exc}")
            if required_group not in sent:
                detail = "; ".join(errors) or "no sendMessage response"
                raise NotifyError(
                    f"{NORTH_GROUP_TITLE} ({required_group}) did not receive the report. {detail}"
                )
        if sent:
            destinations.append(f"telegram:@{username}:{','.join(sent)}")
        elif errors:
            raise NotifyError("Telegram delivery failed: " + "; ".join(errors))
    if webhook:
        _post_webhook(webhook, payload, opener=opener, timeout=timeout)
        destinations.append(webhook)
    if not destinations:
        raise NotifyError(
            f"No Telegram destination. Set {TOKEN_ENV} plus {CHAT_ENV} and "
            f"{GROUP_ENV} for @Mr_North_bot "
            "(not @THWellness_bot or @PirateEye_bot). Optional extra: ALERT_WEBHOOK_URL."
        )
    return NotifyResult(
        delivered=True,
        dry_run=False,
        text=text,
        payload=payload,
        destination=",".join(destinations),
        status="sent",
    )
