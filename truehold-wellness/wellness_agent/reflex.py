"""Fire TrueHold Wellness order/email reflexes with the full inbox snapshot."""

from __future__ import annotations

from wellness_agent.compose import compose_alert, format_alert
from wellness_agent.models import TRIGGER_TYPES, Alert, AlertTrigger
from wellness_agent.notify import NotifyError, NotifyResult, send_alert
from wellness_agent.snapshot import (
    CATEGORY_FOR_TRIGGER,
    load_current_inbox,
    overlay_category,
    save_inbox_state,
)

HEADLINES = {
    "business": "business inbox",
    "order": "order",
    "payment": "payment",
    "fulfillment": "fulfillment request",
    "shipping": "shipping issue",
    "cancellation": "cancellation/refund",
    "peptide": "peptide message",
    "manual": "manual alert",
}


def build_reflex_alert(trigger_type: str, detail: str) -> Alert:
    if trigger_type not in TRIGGER_TYPES:
        raise ValueError(f"Unknown trigger type: {trigger_type}")
    category = CATEGORY_FOR_TRIGGER[trigger_type]
    inbox = overlay_category(load_current_inbox(), category, detail)
    save_inbox_state(inbox)
    return compose_alert(
        AlertTrigger(
            type=trigger_type,
            headline=HEADLINES[trigger_type],
            detail=detail,
        ),
        inbox=inbox,
    )


def fire_reflex(
    trigger_type: str,
    detail: str,
    *,
    exclude_chats: set[str] | None = None,
    require_destination: bool = False,
) -> NotifyResult:
    """Notify operators/webhook of an order or inbox email. Always includes every category."""
    alert = build_reflex_alert(trigger_type, detail)
    try:
        return send_alert(
            alert,
            exclude_chats=exclude_chats,
            require_destination=require_destination,
        )
    except NotifyError:
        if require_destination:
            raise
        return NotifyResult(
            delivered=False,
            dry_run=False,
            text=format_alert(alert),
            payload={"agent": "truehold-wellness-agent"},
            destination=None,
            status="queued_no_destination",
        )
