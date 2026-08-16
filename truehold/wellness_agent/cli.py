from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from truehold.wellness_agent.compose import compose_alert, format_alert
from truehold.wellness_agent.models import AlertTrigger
from truehold.wellness_agent.notify import NotifyError, send_alert


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="truehold-wellness-agent",
        description=(
            "Compose and send TrueHold Wellness-agent alerts only "
            "(not the TrueHold crypto agent). Every alert includes the full "
            "business-inbox snapshot: orders, payments, fulfillment, shipping, "
            "cancellations/refunds, peptide messages, and other actionable email."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    compose = sub.add_parser("compose", help="Print the Wellness alert that would be sent")
    _add_trigger_args(compose)
    compose.add_argument(
        "--json",
        action="store_true",
        help="Print the structured payload (includes full inbox snapshot) instead of text",
    )

    send = sub.add_parser("send", help="Send a Wellness alert, including the inbox snapshot")
    _add_trigger_args(send)
    send.add_argument(
        "--webhook-url",
        default=None,
        help="Destination webhook. Defaults to WELLNESS_ALERT_WEBHOOK_URL.",
    )
    send.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the payload but do not POST it",
    )
    return parser


def _add_trigger_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--type",
        dest="trigger_type",
        default="business",
        choices=(
            "business",
            "order",
            "payment",
            "fulfillment",
            "shipping",
            "cancellation",
            "peptide",
            "manual",
        ),
        help="Wellness-agent trigger type. Crypto/macro triggers are out of scope.",
    )
    parser.add_argument(
        "--headline",
        default=None,
        help="Trigger headline. Defaults from the trigger type.",
    )
    parser.add_argument(
        "--detail",
        default="",
        help="Optional trigger detail shown above the inbox snapshot.",
    )


def _default_headline(trigger_type: str) -> str:
    defaults = {
        "business": "business inbox",
        "order": "order",
        "payment": "payment",
        "fulfillment": "fulfillment request",
        "shipping": "shipping issue",
        "cancellation": "cancellation/refund",
        "peptide": "peptide message",
        "manual": "manual alert",
    }
    return defaults[trigger_type]


def _trigger_from_args(args: argparse.Namespace) -> AlertTrigger:
    return AlertTrigger(
        type=args.trigger_type,
        headline=args.headline or _default_headline(args.trigger_type),
        detail=args.detail,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    alert = compose_alert(_trigger_from_args(args))
    if args.command == "compose":
        if args.json:
            from truehold.wellness_agent.notify import alert_payload

            sys.stdout.write(json.dumps(alert_payload(alert), indent=2) + "\n")
        else:
            sys.stdout.write(format_alert(alert))
        return 0
    try:
        result = send_alert(
            alert,
            webhook_url=args.webhook_url,
            dry_run=args.dry_run,
        )
    except NotifyError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    if result.dry_run:
        sys.stdout.write(result.text)
        sys.stderr.write("dry-run: Wellness inbox snapshot included; webhook not called\n")
        return 0
    sys.stdout.write(result.text)
    sys.stderr.write(f"sent: {result.destination}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
