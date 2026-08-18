"""Local CLI for seed, ingest, match, live Telegram polling, and channel tests."""

from __future__ import annotations

import argparse
import json
import time

from app.config import PROJECT_ROOT, get_settings
from app.db import get_session_factory, init_db
from app.services.demo import run_demo
from app.services.matching.runner import OpportunityMatcher
from app.services.mls.ingest import ListingIngestService
from app.services.providers import get_email_provider, get_mls_provider, get_sms_provider, get_telegram_provider
from app.services.seed import seed_pirates_ig, seed_realtor
from app.services.sms.relay import resolve_sms_destination
from app.services.telegram.inbound import process_telegram_update
from app.services.telegram.realtor_agent import RealtorTelegramService

OFFSET_PATH = PROJECT_ROOT / "data" / "telegram_offset.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Realtor acquisition agent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    sub.add_parser("demo")
    sub.add_parser("ingest")
    sub.add_parser("match")
    sub.add_parser("alert", help="Ingest, match, and send Telegram alerts without auto-approving")
    sub.add_parser("send-test-email", help="Send a ping to EMAIL_RELAY_TO via the configured provider")
    sub.add_parser("send-test-sms", help="Send a ping to SMS_RELAY_TO (mock outbox unless Twilio is live)")
    poll = sub.add_parser("telegram-poll", help="Long-poll Telegram getUpdates for phone approve/reject/snooze")
    poll.add_argument("--once", action="store_true", help="Fetch one batch and exit")
    args = parser.parse_args(argv)

    if args.command == "send-test-email":
        return _send_test_email()
    if args.command == "send-test-sms":
        return _send_test_sms()

    init_db()
    db = get_session_factory()()
    try:
        if args.command == "seed":
            realtor = seed_realtor(db)
            investor = seed_pirates_ig(db, realtor)
            db.commit()
            print(f"Seeded realtor {realtor.public_id} and investor {investor.public_id}")
            return 0
        if args.command == "demo":
            result = run_demo(db)
            db.commit()
            print(result)
            return 0
        realtor = seed_realtor(db)
        seed_pirates_ig(db, realtor)
        if args.command == "ingest":
            result = ListingIngestService(db, get_mls_provider()).sync(realtor)
            db.commit()
            print(result)
            return 0
        if args.command == "match":
            created = OpportunityMatcher(db).match_all(realtor)
            db.commit()
            print({"created": [item.public_id for item in created]})
            return 0
        if args.command == "alert":
            ListingIngestService(db, get_mls_provider()).sync(realtor)
            created = OpportunityMatcher(db).match_all(realtor)
            telegram = RealtorTelegramService(db)
            sent = []
            for opportunity in created:
                telegram.alert_opportunity(realtor, opportunity)
                sent.append(opportunity.public_id)
            db.commit()
            print({"alerted": sent, "telegram_chat_id": realtor.telegram_chat_id})
            return 0
        if args.command == "telegram-poll":
            return _telegram_poll(db, realtor, once=args.once)
    finally:
        db.close()
    return 1


def _send_test_email() -> int:
    settings = get_settings()
    provider = get_email_provider(settings)
    result = provider.send_email(
        settings.email_relay_to,
        f"{settings.email_subject_prefix} SMTP ping".strip(),
        "realtor-agent test email from send-test-email. Relays stay on until testing is confirmed.",
        from_address=settings.email_from,
        intended_recipient="test-operator@local",
    )
    print(result)
    return 0


def _send_test_sms() -> int:
    settings = get_settings()
    dest = resolve_sms_destination(settings.sms_relay_to or "unknown", settings)
    if not dest.get("to"):
        print(
            {
                "ok": False,
                "error": "Set SMS_RELAY_TO to your test phone before live Twilio. Mock SMS still needs a destination.",
            }
        )
        return 1
    provider = get_sms_provider(settings)
    result = provider.send_sms(dest["to"], "[realtor-agent test] SMS ping. Do not send this to Damian or investors yet.")
    result["relay"] = dest
    print(result)
    return 0


def _telegram_poll(db, realtor, *, once: bool) -> int:
    settings = get_settings()
    if settings.telegram_mode != "live":
        print({"ok": False, "error": "Set TELEGRAM_MODE=live and TELEGRAM_BOT_TOKEN, then retry."})
        return 1
    telegram = get_telegram_provider(settings)
    telegram.delete_webhook(drop_pending_updates=False)
    offset = _read_offset()
    print({"ok": True, "polling": True, "offset": offset, "hint": "Open the bot and send /start"})
    while True:
        updates = telegram.get_updates(offset=offset, timeout=25)
        for update in updates:
            offset = int(update["update_id"]) + 1
            _write_offset(offset)
            result = process_telegram_update(db, realtor, update, telegram=telegram)
            db.commit()
            print({"update_id": update.get("update_id"), "result": result})
        if once:
            return 0
        if not updates:
            time.sleep(1)


def _read_offset() -> int | None:
    if not OFFSET_PATH.exists():
        return None
    try:
        data = json.loads(OFFSET_PATH.read_text(encoding="utf-8"))
        return data.get("offset")
    except json.JSONDecodeError:
        return None


def _write_offset(offset: int) -> None:
    OFFSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_PATH.write_text(json.dumps({"offset": offset}), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
