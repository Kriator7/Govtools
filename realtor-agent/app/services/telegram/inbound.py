"""Process inbound Telegram updates from polling or the webhook."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.realtor import Realtor
from app.services.providers import get_telegram_provider
from app.services.seed import is_damian_telegram_user, link_damian_telegram
from app.services.sms.investor_notify import InvestorNotificationService
from app.services.telegram.realtor_agent import RealtorTelegramService

GROUP_INTRO = (
    "PirateEye is live in this group.\n"
    "Listing cards post here. Tap APPROVE / REJECT / SNOOZE / DETAILS on each card.\n"
    "This is still the test flow: investor SMS/email stay on the relay. "
    "Approve does not text Damian or investors.\n"
)


def process_telegram_update(
    db: Session,
    realtor: Realtor,
    payload: dict,
    *,
    telegram=None,
) -> dict:
    telegram = telegram or get_telegram_provider()
    message = payload.get("message") or payload.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    members = message.get("new_chat_members") or []
    for member in members:
        if member.get("is_bot"):
            continue
        damian = link_damian_telegram(db, member, chat_id or None)
        if damian is not None:
            if chat_id:
                realtor.telegram_chat_id = chat_id
                telegram.send_message(
                    chat_id,
                    (
                        f"{GROUP_INTRO}"
                        f"Linked Damian Einbinder (@{(member.get('username') or '').lstrip('@')}).\n"
                        f"chat_id={chat_id}"
                    ),
                )
            return {
                "ok": True,
                "action": "damian_joined",
                "chat_id": chat_id,
                "telegram_user_id": damian.telegram_user_id,
            }

    text = str(message.get("text") or "").strip()
    if text.startswith("/start") or text.lower() in {"/id", "id"}:
        from_user = message.get("from") or {}
        if chat_id:
            realtor.telegram_chat_id = chat_id
            if is_damian_telegram_user(from_user):
                link_damian_telegram(db, from_user, chat_id)
            else:
                realtor.telegram_user_id = str(from_user.get("id") or chat_id)
            telegram.send_message(chat_id, _start_reply(chat, from_user, chat_id))
            return {"ok": True, "action": "linked", "chat_id": chat_id}

    callback = payload.get("callback_query") or {}
    data = callback.get("data")
    if not data:
        return {"ok": True, "ignored": True}

    callback_id = callback.get("id")
    if callback_id:
        telegram.answer_callback_query(str(callback_id), text="Working…")

    from_user = callback.get("from") or {}
    if is_damian_telegram_user(from_user):
        callback_chat = str(((callback.get("message") or {}).get("chat") or {}).get("id") or chat_id or "")
        link_damian_telegram(db, from_user, callback_chat or None)

    service = RealtorTelegramService(db)
    result = service.handle_callback(realtor, data)
    reply_chat_id = str(
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
    if reply_chat_id:
        telegram.send_message(reply_chat_id, _reply_text(result))
    return result


def _start_reply(chat: dict, from_user: dict, chat_id: str) -> str:
    chat_type = str(chat.get("type") or "")
    if chat_type in {"group", "supergroup"} or is_damian_telegram_user(from_user):
        return f"{GROUP_INTRO}chat_id={chat_id}"
    return (
        "Linked as Test Operator.\n"
        "You will get listing alerts here.\n"
        "Approve / Reject / Snooze on each card.\n"
        "Investor SMS is relayed to SMS_RELAY_TO when set; "
        "email copies go to cardanomint@gmail.com while relay mode is on.\n"
        f"chat_id={chat_id}"
    )


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
