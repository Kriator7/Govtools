from __future__ import annotations

from truehold.crypto_agent.catalyst import load_current_catalyst
from truehold.crypto_agent.models import Alert, AlertTrigger, CatalystBriefing


def compose_alert(
    trigger: AlertTrigger,
    catalyst: CatalystBriefing | None = None,
) -> Alert:
    """Build a TrueHold crypto-only alert that always includes the catalyst briefing."""
    return Alert(
        trigger=trigger,
        catalyst=catalyst or load_current_catalyst(),
    )


def format_catalyst(catalyst: CatalystBriefing) -> str:
    """Render the crypto/macro catalyst briefing. No Wellness/business inbox section."""
    blocks = [catalyst.title, "", catalyst.summary]
    labeled = (
        ("Why this matters to our money-flow watch", catalyst.why_it_matters),
        ("Crypto", catalyst.crypto),
        ("Watch next", catalyst.watch_next),
    )
    for label, body in labeled:
        blocks.extend(["", f"{label}: {body}"])
    return "\n".join(blocks).rstrip() + "\n"


def format_alert(alert: Alert) -> str:
    """Human-readable crypto alert: trigger first, then the catalyst briefing."""
    trigger_lines = [f"TrueHold crypto alert — {alert.trigger.headline}"]
    if alert.trigger.detail:
        trigger_lines.extend(["", alert.trigger.detail])
    trigger_block = "\n".join(trigger_lines).rstrip()
    catalyst_block = format_catalyst(alert.catalyst)
    if alert.trigger.type == "geopolitical_catalyst":
        return catalyst_block
    return f"{trigger_block}\n\n---\n\n{catalyst_block}"
