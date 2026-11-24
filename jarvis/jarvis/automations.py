"""Initial automations. They stay disabled until sources, approval, and a verified notification channel exist."""

from __future__ import annotations

AUTOMATIONS = (
    {
        "name": "TrueHold Daily Intelligence",
        "cron": "30 7 * * *",
        "tool": "generate_morning_intelligence",
        "arguments": {},
        "workflow": "truehold-daily-intelligence.json",
        "requires": ("notification_channel",),
    },
    {
        "name": "Unified Action Alerts",
        "cron": "*/15 * * * *",
        "tool": "monitor_priority_email",
        "arguments": {},
        "workflow": "unified-action-alerts.json",
        "requires": ("notification_channel", "email"),
    },
    {
        "name": "AMINT Infrastructure Monitoring",
        "cron": "*/5 * * * *",
        "tool": "check_node_health",
        "arguments": {},
        "workflow": "amint-infrastructure-monitoring.json",
        "requires": ("notification_channel", "cardano_node"),
    },
    {
        "name": "Daily Calendar Briefing",
        "cron": "0 7 * * *",
        "tool": "get_daily_schedule",
        "arguments": {},
        "workflow": "daily-calendar-briefing.json",
        "requires": ("notification_channel", "calendar"),
    },
    {
        "name": "Wellness Operations Review",
        "cron": "0 8 * * *",
        "tool": "generate_business_report",
        "arguments": {},
        "workflow": "wellness-operations-review.json",
        "requires": ("notification_channel", "business_ledger"),
    },
    {
        "name": "Evening Task Reconciliation",
        "cron": "30 18 * * *",
        "tool": "list_tasks",
        "arguments": {},
        "workflow": "evening-task-reconciliation.json",
        "requires": ("notification_channel",),
    },
)

AUTOMATION_NAMES = {item["name"] for item in AUTOMATIONS}
