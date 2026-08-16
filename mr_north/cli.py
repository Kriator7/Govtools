from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from mr_north.compose import compose_alert, format_alert
from mr_north.models import AlertTrigger
from mr_north.notify import NotifyError, send_alert


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mr-north",
        description=(
            "Mr North — TrueHold crypto agent. Compose and send crypto/macro alerts. "
            "Every alert includes the current geopolitical/market catalyst briefing. "
            "TrueHold Wellness is a separate agent and is not modified here."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    compose = sub.add_parser("compose", help="Print the alert that would be sent")
    _add_trigger_args(compose)
    compose.add_argument(
        "--json",
        action="store_true",
        help="Print the structured payload (includes catalyst data) instead of text",
    )

    send = sub.add_parser("send", help="Send an Mr North alert, including catalyst data")
    _add_trigger_args(send)
    send.add_argument(
        "--webhook-url",
        default=None,
        help="Destination webhook. Defaults to ALERT_WEBHOOK_URL.",
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
        default="geopolitical_catalyst",
        choices=(
            "geopolitical_catalyst",
            "btc_threshold",
            "capital_regime",
            "macro_liquidity",
            "manual",
        ),
        help="Mr North trigger type. TrueHold Wellness inbox triggers are out of scope.",
    )
    parser.add_argument(
        "--headline",
        default=None,
        help="Trigger headline. Defaults from the trigger type.",
    )
    parser.add_argument(
        "--detail",
        default="",
        help="Optional trigger detail shown above the catalyst briefing.",
    )


def _default_headline(trigger_type: str) -> str:
    defaults = {
        "geopolitical_catalyst": "geopolitical / market catalyst",
        "btc_threshold": "BTC threshold",
        "capital_regime": "capital-regime transition",
        "macro_liquidity": "Macro Liquidity",
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
            from mr_north.notify import alert_payload

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
        sys.stderr.write("dry-run: Mr North catalyst briefing included; webhook not called\n")
        return 0
    sys.stdout.write(result.text)
    sys.stderr.write(f"sent: {result.destination}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
