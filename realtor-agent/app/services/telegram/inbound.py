"""Process inbound Telegram updates from polling or the webhook."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.realtor import Realtor
from app.services.open_leads.hunt import OpenLeadHuntService
from app.services.providers import get_telegram_provider
from app.services.sms.investor_notify import InvestorNotificationService
from app.services.telegram.realtor_agent import RealtorTelegramService


def process_telegram_update(
    db: Session,
    realtor: Realtor,
    payload: dict,
    *,
    telegram=None,
) -> dict:
    telegram = telegram or get_telegram_provider()
    message = payload.get("message") or payload.get("edited_message") or {}
    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    if text.startswith("/start") or text.lower() in {"/id", "id"}:
        chat_id = str(chat.get("id") or "")
        from_user = message.get("from") or {}
        if chat_id:
            realtor.telegram_chat_id = chat_id
            realtor.telegram_user_id = str(from_user.get("id") or chat_id)
            telegram.send_message(
                chat_id,
                (
                    "Linked as Test Operator.\n"
                    "You will get listing alerts here.\n"
                    "MLS is still mock — send /hunt for public obituaries, FSBO, HUD, and probate notices.\n"
                    "Approve / Reject / Snooze on each card.\n"
                    "Investor SMS is relayed to SMS_RELAY_TO when set; "
                    "email copies go to cardanomint@gmail.com while relay mode is on.\n"
                    f"chat_id={chat_id}"
                ),
            )
            return {"ok": True, "action": "linked", "chat_id": chat_id}

    if text:
        hunt = _maybe_hunt_command(db, realtor, telegram, text, str(chat.get("id") or realtor.telegram_chat_id or ""))
        if hunt is not None:
            return hunt

    callback = payload.get("callback_query") or {}
    data = callback.get("data")
    if not data:
        return {"ok": True, "ignored": True}

    callback_id = callback.get("id")
    if callback_id:
        telegram.answer_callback_query(str(callback_id), text="Working…")

    chat_id = str(
        ((callback.get("message") or {}).get("chat") or {}).get("id")
        or realtor.telegram_chat_id
        or ""
    )
    if str(data).startswith("lead:"):
        result = _handle_lead_callback(db, realtor, str(data))
        if chat_id:
            telegram.send_message(chat_id, result.get("text") or "Done.")
        return result

    service = RealtorTelegramService(db)
    result = service.handle_callback(realtor, data)
    if result.get("action") == "approve" and result.get("ok"):
        public_id = data.split(":", 1)[1]
        opportunity = (
            db.query(Opportunity)
            .filter(Opportunity.public_id == public_id, Opportunity.realtor_id == realtor.id)
            .one_or_none()
        )
        if opportunity:
            InvestorNotificationService(db).notify_approved(realtor, opportunity)
            result["notified"] = True
    if chat_id:
        telegram.send_message(chat_id, _reply_text(result))
    return result


def _maybe_hunt_command(db: Session, realtor: Realtor, telegram, text: str, chat_id: str) -> dict | None:
    from app.services.telegram.open_leads import (
        HELP_TEXT,
        MLS_STATUS_TEXT,
        empty_leads_text,
        hunt_source_for_text,
        lead_card,
        summary_text,
    )

    kind = hunt_source_for_text(text)
    if kind == "unknown":
        return None
    if not chat_id:
        return {"ok": False, "action": "hunt", "error": "no chat id"}
    if kind == "help":
        telegram.send_message(chat_id, HELP_TEXT)
        return {"ok": True, "action": "help"}
    if kind == "mls":
        telegram.send_message(chat_id, MLS_STATUS_TEXT)
        return {"ok": True, "action": "mls-status"}
    hunt = OpenLeadHuntService(db)
    if kind == "leads":
        leads = hunt.recent(realtor)
        if not leads:
            telegram.send_message(chat_id, empty_leads_text(None))
            return {"ok": True, "action": "leads", "count": 0}
        telegram.send_message(chat_id, f"{len(leads)} stored public lead(s). Newest first.")
        for lead in leads[:8]:
            body, buttons = lead_card(lead)
            telegram.send_message(chat_id, body, buttons)
        return {"ok": True, "action": "leads", "count": len(leads)}
    source = kind  # None means all sources
    result = hunt.hunt(realtor, source=source)
    db.commit()
    telegram.send_message(chat_id, summary_text(result, source=source))
    posted = 0
    for public_id in result.get("lead_ids") or []:
        lead = hunt.get(realtor, public_id)
        if lead is None:
            continue
        body, buttons = lead_card(lead)
        telegram.send_message(chat_id, body, buttons)
        posted += 1
        if posted >= 8:
            break
    return {"ok": True, "action": "hunt", "source": source, **result}


def _handle_lead_callback(db: Session, realtor: Realtor, data: str) -> dict:
    parts = data.split(":")
    if len(parts) < 3:
        return {"ok": False, "action": "lead", "error": "bad callback"}
    _, verb, public_id = parts[0], parts[1], parts[2]
    hunt = OpenLeadHuntService(db)
    if verb == "keep":
        lead = hunt.set_status(realtor, public_id, "kept")
        if lead is None:
            return {"ok": False, "action": "lead-keep", "error": "unknown lead"}
        db.commit()
        return {"ok": True, "action": "lead-keep", "lead_id": public_id, "text": f"Kept {public_id} for follow-up. Assessor is still public-search only."}
    if verb == "dismiss":
        lead = hunt.set_status(realtor, public_id, "dismissed")
        if lead is None:
            return {"ok": False, "action": "lead-dismiss", "error": "unknown lead"}
        db.commit()
        return {"ok": True, "action": "lead-dismiss", "lead_id": public_id, "text": f"Dismissed {public_id}."}
    return {"ok": False, "action": "lead", "error": verb}


def _reply_text(result: dict) -> str:
    if not result.get("ok"):
        return f"Could not handle that button: {result.get('error') or 'unknown error'}"
    action = result.get("action")
    oid = result.get("opportunity_id") or ""
    if action == "approve":
        return f"Approved {oid}. Investor notify ran (SMS relay + email copy if enabled)."
    if action == "reject":
        return f"Rejected {oid}."
    if action == "snooze":
        return f"Snoozed {oid} for 24 hours."
    if action == "details":
        details = result.get("details") or {}
        listing = details.get("listing") or {}
        return (
            f"Details {details.get('opportunity_id')}\n"
            f"Status: {details.get('status')}\n"
            f"Score: {details.get('score')}\n"
            f"Address: {listing.get('address')}\n"
            f"URL: {listing.get('url') or 'n/a'}\n"
            f"{details.get('review_notice')}"
        )
    if action == "view":
        return result.get("url") or "No listing URL on file."
    return f"Done ({action})."
