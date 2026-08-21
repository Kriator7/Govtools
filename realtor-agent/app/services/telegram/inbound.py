"""Process inbound Telegram updates from polling or the webhook."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.realtor import Realtor
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
                    "Approve / Reject / Snooze on each card.\n"
                    "Investor SMS is relayed to SMS_RELAY_TO when set; "
                    "email copies go to cardanomint@gmail.com while relay mode is on.\n"
                    f"chat_id={chat_id}"
                ),
            )
            return {"ok": True, "action": "linked", "chat_id": chat_id}

    callback = payload.get("callback_query") or {}
    data = callback.get("data")
    if not data:
        return {"ok": True, "ignored": True}

    callback_id = callback.get("id")
    if callback_id:
        telegram.answer_callback_query(str(callback_id), text="Working…")

    service = RealtorTelegramService(db)
    result = service.handle_callback(realtor, data)
    chat_id = str(
        ((callback.get("message") or {}).get("chat") or {}).get("id")
        or realtor.telegram_chat_id
        or ""
    )
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
