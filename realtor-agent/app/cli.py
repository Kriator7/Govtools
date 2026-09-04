"""Local CLI for seed, ingest, match, live Telegram polling, and channel tests."""

from __future__ import annotations

import argparse
import json
import time
from email.message import EmailMessage
from pathlib import Path

from app.config import PROJECT_ROOT, get_settings
from app.db import get_session_factory, init_db
from app.services.demo import run_demo
from app.services.matching.runner import OpportunityMatcher
from app.services.mls.ingest import ListingIngestService
from app.services.open_leads.hunt import OpenLeadHuntService
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
    inbox = sub.add_parser(
        "inbox-poll",
        help="Watch Gmail for Damian packet replies and apply them to realtor packet data",
    )
    inbox.add_argument("--once", action="store_true", help="Poll once and exit")
    hunt = sub.add_parser(
        "hunt",
        help="Search public obituaries, FSBO, HUD/REO, and probate notices (no MLS scrape)",
    )
    hunt.add_argument(
        "--source",
        choices=["obituary", "fsbo", "hud", "probate"],
        help="One public source; default is all",
    )
    apply_mail = sub.add_parser(
        "inbox-apply",
        help="Apply a pasted packet email (file) to realtor packet data",
    )
    apply_mail.add_argument("--from-address", required=True)
    apply_mail.add_argument("--to", default="jrupe7@gmail.com")
    apply_mail.add_argument("--subject", required=True)
    apply_mail.add_argument("--body-file", required=True)
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
        if args.command == "inbox-poll":
            from app.services.inbox.watch import poll_forever

            return poll_forever(db, once=args.once)
        if args.command == "inbox-apply":
            return _inbox_apply(db, args)
        if args.command == "hunt":
            return _hunt_open_leads(db, source=args.source)
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


def _inbox_apply(db, args) -> int:
    from app.services.inbox.apply import PacketIntakeService
    from app.services.inbox.message import parse_rfc822
    from app.services.inbox.status import write_intake_snapshot

    body_path = Path(args.body_file)
    if not body_path.is_file():
        print({"ok": False, "error": f"body file not found: {body_path}"})
        return 1
    message = EmailMessage()
    message["From"] = args.from_address
    message["To"] = args.to
    message["Subject"] = args.subject
    message["Message-ID"] = f"<inbox-apply-{body_path.name}@local>"
    message.set_content(body_path.read_text(encoding="utf-8"))
    inbound = parse_rfc822(message.as_bytes(), account="pasted", uid="apply")
    result = PacketIntakeService(db).apply_message(inbound)
    db.commit()
    snapshot = write_intake_snapshot(db)
    result["snapshot"] = str(snapshot)
    print(json.dumps(result, default=str))
    return 0 if result.get("status") != "ignored" else 1


def _hunt_open_leads(db, *, source: str | None) -> int:
    realtor = seed_realtor(db)
    seed_pirates_ig(db, realtor)
    hunt = OpenLeadHuntService(db)
    result = hunt.hunt(realtor, source=source)
    db.commit()
    chat_id = realtor.telegram_chat_id
    settings = get_settings()
    if settings.telegram_mode == "live" and chat_id and chat_id not in {"", "mock-realtor"}:
        from app.services.telegram.open_leads import lead_card, summary_text

        telegram = get_telegram_provider(settings)
        telegram.send_message(chat_id, summary_text(result, source=source))
        for public_id in (result.get("lead_ids") or [])[:8]:
            lead = hunt.get(realtor, public_id)
            if lead is None:
                continue
            body, buttons = lead_card(lead)
            telegram.send_message(chat_id, body, buttons)
        result["telegram"] = chat_id
    print(json.dumps(result, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
