from __future__ import annotations

import argparse
import json
import os
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
        help=f"Receive picture-menu orders and staff /inbox on @{REQUIRED_USERNAME}",
    )
    poll.add_argument("--once", action="store_true")
    sub.add_parser("whoami", help=f"Call Telegram getMe and confirm @{REQUIRED_USERNAME}")
    sub.add_parser(
        "configure-telegram",
        help=f"Set @{REQUIRED_USERNAME} name, description, and command menu",
    )
    sub.add_parser("catalog", help="Print the live TrueHold Wellness shop inventory")
    sub.add_parser("stock", help="Print on-hand inventory counts and recent adjustments")
    product = sub.add_parser("product", help="Resolve a SKU and print its locked-sheet path")
    product.add_argument("query", help="Product name or alias, for example klow or tirzepatide")
    ingest = sub.add_parser(
        "ingest-email",
        help="Run order/payment/fulfillment/shipping/cancellation/peptide email reflexes",
    )
    ingest.add_argument(
        "--path",
        default=None,
        help="JSON inbox. Defaults to EMAIL_INBOX_PATH or data/imports/sample_reflex_emails.json",
    )
    files = sub.add_parser(
        "ingest-files",
        help="Import old-agent PDFs and trueholdwellness-orders.xlsx from data/imports/legacy/",
    )
    files.add_argument(
        "--path",
        default=None,
        help="Folder of Finder exports. Defaults to data/imports/legacy/",
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
    if args.command == "catalog":
        from wellness_agent.catalog import format_catalog

        sys.stdout.write(format_catalog())
        return 0
    if args.command == "stock":
        from wellness_agent.stock import format_stock

        sys.stdout.write(format_stock())
        return 0
    if args.command == "product":
        from wellness_agent.catalog import (
            UnknownProductError,
            find_product,
            pdf_path,
            telegram_file_path,
        )

        try:
            item = find_product(args.query)
            path = pdf_path(item)
            telegram_path = telegram_file_path(item)
        except (UnknownProductError, FileNotFoundError) as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 1
        sys.stdout.write(
            json.dumps(
                {
                    "ok": True,
                    "id": item["id"],
                    "pdf": str(path),
                    "telegram_file": str(telegram_path),
                }
            )
            + "\n"
        )
        return 0
    if args.command == "ingest-email":
        from pathlib import Path

        from wellness_agent.email_reflex import ingest_reflex_emails
        from wellness_agent.envfile import PACKAGE_ROOT

        inbox = Path(
            args.path
            or os.environ.get("EMAIL_INBOX_PATH")
            or (PACKAGE_ROOT / "data" / "imports" / "sample_reflex_emails.json")
        )
        if not inbox.is_absolute():
            inbox = PACKAGE_ROOT / inbox
        fired = ingest_reflex_emails(inbox)
        sys.stdout.write(json.dumps({"ok": True, "fired": fired}, indent=2) + "\n")
        return 0
    if args.command == "ingest-files":
        from pathlib import Path

        from wellness_agent.envfile import PACKAGE_ROOT
        from wellness_agent.ingest_files import ingest_legacy

        folder = Path(args.path) if args.path else (PACKAGE_ROOT / "data" / "imports" / "legacy")
        if not folder.is_absolute():
            folder = PACKAGE_ROOT / folder
        result = ingest_legacy(folder)
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
        return 0
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
    from wellness_agent.catalog import sync_telegram_files
    from wellness_agent.inventory.build_agent import ensure_agent
    from wellness_agent.knowledge import seed_approved_knowledge

    telegram = WellnessTelegram(token)
    telegram.assert_identity()
    sync_telegram_files()
    ensure_agent()
    seed_approved_knowledge()
    try:
        telegram.configure_public_profile()
    except Exception as exc:
        sys.stderr.write(f"configure-telegram skipped: {exc}\n")
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
    sys.stdout.flush()
    while True:
        try:
            updates = telegram.get_updates(offset=offset, timeout=25)
        except Exception as exc:
            sys.stderr.write(f"telegram poll retry: {exc}\n")
            sys.stderr.flush()
            if once:
                return 1
            time.sleep(2)
            continue
        for update in updates:
            offset = int(update["update_id"]) + 1
            offset_path.parent.mkdir(parents=True, exist_ok=True)
            offset_path.write_text(json.dumps({"offset": offset}), encoding="utf-8")
            try:
                result = handle_telegram_update(update, telegram)
                sys.stdout.write(
                    json.dumps({"update_id": update.get("update_id"), "result": result}) + "\n"
                )
                sys.stdout.flush()
            except Exception as exc:
                sys.stderr.write(
                    json.dumps({"update_id": update.get("update_id"), "error": str(exc)}) + "\n"
                )
                sys.stderr.flush()
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
