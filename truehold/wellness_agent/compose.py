from __future__ import annotations

from truehold.wellness_agent.models import Alert, AlertTrigger, InboxSnapshot
from truehold.wellness_agent.snapshot import load_current_inbox

CATEGORY_LABELS = (
    ("orders", "Orders"),
    ("payments", "Payments"),
    ("fulfillment", "Fulfillment"),
    ("shipping", "Shipping"),
    ("cancellations", "Cancellations"),
    ("peptides", "Peptides"),
    ("other_actionable", "Other actionable"),
)


def compose_alert(
    trigger: AlertTrigger,
    inbox: InboxSnapshot | None = None,
) -> Alert:
    """Build a TrueHold Wellness-only alert that always includes the full inbox snapshot."""
    return Alert(
        trigger=trigger,
        inbox=inbox or load_current_inbox(),
    )


def format_inbox(inbox: InboxSnapshot) -> str:
    """Render the Wellness inbox snapshot with every business category present."""
    blocks = [inbox.title, "", f"Business: {inbox.copy}"]
    for key, label in CATEGORY_LABELS:
        status = inbox.categories()[key]
        flag = "NEW" if status.new else "none"
        blocks.extend(["", f"{label}: [{flag}] {status.detail}"])
    blocks.extend(["", f"Inbox: {inbox.inbox_note}"])
    return "\n".join(blocks).rstrip() + "\n"


def format_alert(alert: Alert) -> str:
    """Human-readable Wellness alert: trigger first when needed, then the full inbox snapshot."""
    inbox_block = format_inbox(alert.inbox)
    if alert.trigger.type == "business" and not alert.trigger.detail:
        return inbox_block
    trigger_lines = [f"TrueHold Wellness alert — {alert.trigger.headline}"]
    if alert.trigger.detail:
        trigger_lines.extend(["", alert.trigger.detail])
    trigger_block = "\n".join(trigger_lines).rstrip()
    return f"{trigger_block}\n\n---\n\n{inbox_block}"
