from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from mr_north.compose import compose_alert, format_alert
from mr_north.models import AlertTrigger
from mr_north.notify import NotifyError, send_alert
from mr_north.envfile import load_local_env


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
    hourly = sub.add_parser(
        "hourly",
        help="Fetch official BLS prints and send the hourly breakdown",
    )
    hourly.add_argument(
        "--webhook-url",
        default=None,
        help="Destination webhook. Defaults to ALERT_WEBHOOK_URL.",
    )
    hourly.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and save the report but do not POST it",
    )
    sub.add_parser(
        "hourly-loop",
        help=(
            "Run forever: larger catalyst briefing, hourly BLS, and immediate "
            "BTC watches. Restart with mr_north/scripts/keep_hourly.sh"
        ),
    )
    sub.add_parser(
        "hourly-status",
        help="Show whether the last hourly BLS report was delivered",
    )
    watch = sub.add_parser(
        "watch",
        help="Check BTC and send immediately to both chats on a material change",
    )
    watch.add_argument(
        "--webhook-url",
        default=None,
        help="Destination webhook. Defaults to ALERT_WEBHOOK_URL.",
    )
    watch.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch BTC and decide, but do not send Telegram",
    )
    catalyst = sub.add_parser(
        "catalyst",
        help="Send the larger geopolitical / market briefing to both chats",
    )
    catalyst.add_argument(
        "--webhook-url",
        default=None,
        help="Destination webhook. Defaults to ALERT_WEBHOOK_URL.",
    )
    catalyst.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the briefing but do not send Telegram",
    )
    sub.add_parser(
        "telegram-whoami",
        help="Call Telegram getMe and refuse Wellness/realtor bots",
    )
    sub.add_parser(
        "destinations",
        help="Print operator + MaximumMint & North chat ids (never PirateEye)",
    )
    sub.add_parser(
        "telegram-capture",
        help=(
            "One-shot: bind James and/or MaximumMint & North from Telegram "
            "(includes bot-added-to-group events)"
        ),
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
            "hourly_bls",
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
        "hourly_bls": "hourly BLS breakdown",
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
    if args.command == "hourly-status":
        from mr_north.hourly import hourly_status

        status = hourly_status()
        sys.stdout.write(json.dumps(status) + "\n")
        return 0 if status.get("ok") else 1
    if args.command == "hourly-loop":
        from mr_north.hourly import hourly_loop

        return hourly_loop()
    if args.command == "hourly":
        from mr_north.hourly import run_hourly

        result = run_hourly(dry_run=args.dry_run, webhook_url=args.webhook_url)
        sys.stdout.write(result["text"])
        if not result.get("ok"):
            sys.stderr.write(f"error: {result.get('reason')}\n")
            return 1
        if result.get("dry_run"):
            sys.stderr.write("dry-run: hourly BLS breakdown saved; Telegram not called\n")
            return 0
        sys.stderr.write(f"sent: {result.get('destination')}\n")
        return 0
    if args.command == "catalyst":
        from mr_north.hourly import run_catalyst_report

        result = run_catalyst_report(dry_run=args.dry_run, webhook_url=args.webhook_url)
        sys.stdout.write(result["text"])
        if not result.get("ok"):
            sys.stderr.write(f"error: {result.get('reason')}\n")
            return 1
        if result.get("dry_run"):
            sys.stderr.write("dry-run: larger catalyst briefing built; Telegram not called\n")
            return 0
        sys.stderr.write(f"sent: {result.get('destination')}\n")
        return 0
    if args.command == "watch":
        from mr_north.watch import run_market_watch

        result = run_market_watch(dry_run=args.dry_run, webhook_url=args.webhook_url)
        if result.get("text"):
            sys.stdout.write(result["text"])
        else:
            sys.stdout.write(json.dumps({k: v for k, v in result.items() if k != "text"}) + "\n")
        if not result.get("ok"):
            sys.stderr.write(f"error: {result.get('reason')}\n")
            return 1
        if result.get("reason") == "unchanged":
            sys.stderr.write("watch: no material BTC change; Telegram not called\n")
            return 0
        if result.get("dry_run"):
            sys.stderr.write("dry-run: BTC change detected; Telegram not called\n")
            return 0
        sys.stderr.write(f"sent: {result.get('destination')}\n")
        return 0
    if args.command == "telegram-whoami":
        from mr_north.identity import WrongTelegramBotError
        from mr_north.telegram import (
            NORTH_GROUP_TITLE,
            TelegramError,
            configured_chat_ids,
            live_client,
            north_group_chat_id,
        )

        try:
            client = live_client()
            username = client.assert_identity()
            group_id = client.resolve_group_chat_id(north_group_chat_id())
        except (TelegramError, WrongTelegramBotError) as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 1
        sys.stdout.write(
            json.dumps(
                {
                    "ok": True,
                    "bot": username,
                    "chat_ids": configured_chat_ids(),
                    "group_title": NORTH_GROUP_TITLE,
                    "group_chat_id": group_id or north_group_chat_id(),
                    "agent": "mr-north",
                }
            )
            + "\n"
        )
        return 0
    if args.command == "destinations":
        from mr_north.telegram import destination_map

        payload = destination_map()
        sys.stdout.write(json.dumps({"ok": True, **payload}) + "\n")
        return 0 if payload.get("chat_ids") else 1
    if args.command == "telegram-capture":
        from mr_north.identity import WrongTelegramBotError
        from mr_north.telegram import (
            TelegramError,
            live_client,
            save_chat_id,
            save_group_chat_id,
        )

        try:
            client = live_client()
            username = client.assert_identity()
            bound = client.capture_destinations()
            path = None
            if bound.get("group_chat_id"):
                path = save_group_chat_id(bound["group_chat_id"], username=username)
            if bound.get("operator_chat_id"):
                path = save_chat_id(bound["operator_chat_id"], username=username)
        except (TelegramError, WrongTelegramBotError) as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 1
        sys.stdout.write(
            json.dumps(
                {
                    "ok": True,
                    "bot": username,
                    "chat_id": bound.get("operator_chat_id") or bound.get("group_chat_id"),
                    "group_chat_id": bound.get("group_chat_id"),
                    "group_title": bound.get("group_title"),
                    "saved": str(path) if path else "",
                    "agent": "mr-north",
                }
            )
            + "\n"
        )
        return 0
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
        sys.stderr.write("dry-run: Mr North catalyst briefing included; Telegram not called\n")
        return 0
    sys.stdout.write(result.text)
    sys.stderr.write(f"sent: {result.destination}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
