from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from wellness_agent.compose import compose_alert, format_alert
from wellness_agent.envfile import load_local_env
from wellness_agent.identity import REQUIRED_USERNAME
from wellness_agent.models import AlertTrigger
from wellness_agent.notify import NotifyError, send_alert


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
    poll = sub.add_parser(
        "telegram-poll",
        help=f"Receive /start /inbox /order on @{REQUIRED_USERNAME}",
    )
    poll.add_argument("--once", action="store_true")
    sub.add_parser("whoami", help=f"Call Telegram getMe and confirm @{REQUIRED_USERNAME}")
    sub.add_parser(
        "configure-telegram",
        help=f"Set @{REQUIRED_USERNAME} name, description, and command menu",
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
    load_local_env()
    args = _build_parser().parse_args(argv)
    if args.command == "telegram-poll":
        return _telegram_poll(once=args.once)
    if args.command == "whoami":
        return _telegram_whoami()
    if args.command == "configure-telegram":
        return _configure_telegram()
    alert = compose_alert(_trigger_from_args(args))
    if args.command == "compose":
        if args.json:
            from wellness_agent.notify import alert_payload

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


def _telegram_poll(*, once: bool) -> int:
    import os
    import time
    from pathlib import Path

    from wellness_agent.telegram_api import WellnessTelegram
    from wellness_agent.telegram_inbound import handle_telegram_update

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if os.environ.get("TELEGRAM_MODE", "mock") != "live" or not token:
        sys.stderr.write(
            f"error: set TELEGRAM_MODE=live and TELEGRAM_BOT_TOKEN for @{REQUIRED_USERNAME}\n"
        )
        return 1
    telegram = WellnessTelegram(token)
    telegram.assert_identity()
    telegram.configure_public_profile()
    telegram.delete_webhook()
    offset_path = Path(__file__).resolve().parent.parent / "data" / "telegram_offset.json"
    offset = None
    if offset_path.exists():
        try:
            offset = json.loads(offset_path.read_text(encoding="utf-8")).get("offset")
        except json.JSONDecodeError:
            offset = None
    sys.stdout.write(
        json.dumps({"ok": True, "polling": True, "bot": f"@{REQUIRED_USERNAME}", "offset": offset})
        + "\n"
    )
    while True:
        updates = telegram.get_updates(offset=offset, timeout=25)
        for update in updates:
            offset = int(update["update_id"]) + 1
            offset_path.parent.mkdir(parents=True, exist_ok=True)
            offset_path.write_text(json.dumps({"offset": offset}), encoding="utf-8")
            result = handle_telegram_update(update, telegram)
            sys.stdout.write(json.dumps({"update_id": update.get("update_id"), "result": result}) + "\n")
        if once:
            return 0
        if not updates:
            time.sleep(1)


def _live_telegram():
    import os

    from wellness_agent.telegram_api import WellnessTelegram

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if os.environ.get("TELEGRAM_MODE", "mock") != "live" or not token:
        sys.stderr.write(
            f"error: set TELEGRAM_MODE=live and TELEGRAM_BOT_TOKEN for @{REQUIRED_USERNAME}\n"
        )
        return None
    telegram = WellnessTelegram(token)
    telegram.assert_identity()
    return telegram


def _telegram_whoami() -> int:
    telegram = _live_telegram()
    if telegram is None:
        return 1
    me = telegram.get_me()
    sys.stdout.write(
        json.dumps(
            {
                "ok": True,
                "id": me.get("id"),
                "username": me.get("username"),
                "first_name": me.get("first_name"),
                "required": REQUIRED_USERNAME,
            }
        )
        + "\n"
    )
    return 0


def _configure_telegram() -> int:
    telegram = _live_telegram()
    if telegram is None:
        return 1
    result = telegram.configure_public_profile()
    sys.stdout.write(json.dumps({"ok": True, **result}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
