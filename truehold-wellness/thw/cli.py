"""CLI for TrueHold Wellness order emails and @Npeppers_bot. Independent of realtor-agent."""

from __future__ import annotations

import argparse
import json
import time

from thw.config import get_settings
from thw.db import get_session_factory, init_db
from thw.orders import get_or_create_operator, handle_telegram_update, ingest_inbox, notify_order
from thw.providers import get_telegram

OFFSET_PATH_NAME = "data/telegram_offset.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TrueHold Wellness order-email agent (@Npeppers_bot)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo")
    sub.add_parser("ingest")
    sub.add_parser("identity")
    poll = sub.add_parser("telegram-poll")
    poll.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)

    settings = get_settings()
    init_db()
    db = get_session_factory()()
    try:
        if args.command == "identity":
            telegram = get_telegram(settings)
            print({"ok": True, "username": telegram.get_username(), "mode": settings.telegram_mode})
            return 0
        if args.command == "demo":
            get_or_create_operator(db, settings.telegram_operator_chat_id)
            created = ingest_inbox(db, settings.inbox_path)
            telegram = get_telegram(settings)
            for order in created:
                notify_order(db, order, telegram=telegram)
            db.commit()
            print(
                {
                    "ok": True,
                    "agent": "truehold-wellness",
                    "telegram": "@Npeppers_bot",
                    "orders": [item.public_id for item in created],
                }
            )
            return 0
        if args.command == "ingest":
            get_or_create_operator(db, settings.telegram_operator_chat_id)
            created = ingest_inbox(db, settings.inbox_path)
            telegram = get_telegram(settings)
            for order in created:
                notify_order(db, order, telegram=telegram)
            db.commit()
            print({"created": [item.public_id for item in created]})
            return 0
        if args.command == "telegram-poll":
            return _poll(db, once=args.once)
    finally:
        db.close()
    return 1


def _poll(db, *, once: bool) -> int:
    settings = get_settings()
    if settings.telegram_mode != "live":
        print({"ok": False, "error": "Set TELEGRAM_MODE=live with the @Npeppers_bot token."})
        return 1
    telegram = get_telegram(settings)
    telegram.delete_webhook()
    offset = _read_offset()
    print({"ok": True, "polling": True, "bot": "@Npeppers_bot", "offset": offset})
    while True:
        updates = telegram.get_updates(offset=offset, timeout=25)
        for update in updates:
            offset = int(update["update_id"]) + 1
            _write_offset(offset)
            result = handle_telegram_update(db, update, telegram=telegram)
            db.commit()
            print({"update_id": update.get("update_id"), "result": result})
        if once:
            return 0
        if not updates:
            time.sleep(1)


def _offset_path():
    return get_settings().project_root / OFFSET_PATH_NAME


def _read_offset() -> int | None:
    path = _offset_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("offset")
    except json.JSONDecodeError:
        return None


def _write_offset(offset: int) -> None:
    path = _offset_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"offset": offset}), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
