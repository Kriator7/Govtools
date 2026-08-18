"""Inbound Telegram for TrueHold Wellness: picture menu for clients, staff-only inbox."""

from __future__ import annotations

from wellness_agent.access import STAFF_DENIED, claim_staff, is_operator
from wellness_agent.catalog import (
    UnknownProductError,
    find_product,
    format_product_caption,
    pdf_path,
)
from wellness_agent.compose import compose_alert, format_alert
from wellness_agent.identity import REQUIRED_USERNAME
from wellness_agent.menu import CUSTOMER_CONFIRM, handle_menu_callback, send_picture_menu
from wellness_agent.models import AlertTrigger
from wellness_agent.reflex import fire_reflex
from wellness_agent.telegram_copy import (
    BOT_COMMANDS,
    CUSTOMER_COMMANDS,
    CUSTOMER_HELP,
    HELP,
    SCHEDULE,
    STAFF_COMMANDS,
    STAFF_HELP,
)

__all__ = [
    "BOT_COMMANDS",
    "CUSTOMER_COMMANDS",
    "HELP",
    "SCHEDULE",
    "STAFF_COMMANDS",
    "handle_telegram_update",
]


def _command(text: str) -> str:
    if not text:
        return ""
    first = text.split(None, 1)[0].lower()
    if first.startswith("/"):
        first = first[1:]
    if "@" in first:
        first = first.split("@", 1)[0]
    return first


def _rest(text: str) -> str:
    parts = text.split(None, 1)
    return parts[1].strip() if len(parts) > 1 else ""


def _ids(payload_message: dict) -> tuple[str, str, str]:
    chat = payload_message.get("chat") or {}
    sender = payload_message.get("from") or {}
    return (
        str(chat.get("id") or ""),
        str(sender.get("id") or ""),
        str(chat.get("type") or "private"),
    )


def _matched_product(detail: str):
    tokens = [part for part in detail.replace("/", " ").replace(",", " ").split() if len(part) >= 3]
    for token in (detail, *tokens):
        try:
            return find_product(token)
        except UnknownProductError:
            continue
    return None


def _send_sheet(telegram, chat_id: str, query: str) -> dict:
    if not query:
        telegram.send_message(chat_id, "Tap a picture on /menu, or send a product name.")
        return {"ok": True, "action": "product-help", "chat_id": chat_id}
    try:
        product = find_product(query)
        path = pdf_path(product)
    except (UnknownProductError, FileNotFoundError) as exc:
        telegram.send_message(chat_id, str(exc))
        return {"ok": False, "action": "product-miss", "chat_id": chat_id, "error": str(exc)}
    telegram.send_document(chat_id, path, caption=format_product_caption(product))
    return {"ok": True, "action": "product", "chat_id": chat_id, "product": product["id"]}


def handle_telegram_update(payload: dict, telegram) -> dict:
    callback = payload.get("callback_query")
    if callback:
        return handle_menu_callback(callback, telegram)

    message = payload.get("message") or {}
    text = str(message.get("text") or "").strip()
    chat_id, user_id, chat_type = _ids(message)
    if not chat_id:
        return {"ok": True, "ignored": True}

    command = _command(text)
    staff = is_operator(user_id, chat_id, chat_type)

    if command == "staff":
        if staff:
            telegram.send_message(chat_id, STAFF_HELP)
            return {"ok": True, "action": "staff-already", "chat_id": chat_id, "user_id": user_id}
        if claim_staff(_rest(text), chat_id=chat_id, user_id=user_id):
            telegram.send_message(chat_id, STAFF_HELP)
            return {"ok": True, "action": "staff-claimed", "chat_id": chat_id, "user_id": user_id}
        telegram.send_message(chat_id, STAFF_DENIED)
        return {"ok": False, "action": "staff-denied", "chat_id": chat_id}

    if command in {"start", "help", "menu"}:
        if command == "help":
            telegram.send_message(chat_id, STAFF_HELP if staff else CUSTOMER_HELP)
            return {"ok": True, "action": "help", "chat_id": chat_id, "staff": staff}
        if command == "start" and staff:
            telegram.send_message(chat_id, STAFF_HELP)
        send_picture_menu(telegram, chat_id)
        return {"ok": True, "action": "menu", "chat_id": chat_id, "staff": staff}

    if command == "inbox":
        if not staff:
            telegram.send_message(chat_id, STAFF_DENIED)
            return {"ok": False, "action": "staff-denied", "chat_id": chat_id}
        alert = compose_alert(AlertTrigger(type="business", headline="business inbox"))
        telegram.send_message(chat_id, format_alert(alert))
        return {"ok": True, "action": "inbox", "chat_id": chat_id, "staff": True}

    if command == "schedule":
        telegram.send_message(chat_id, SCHEDULE)
        return {"ok": True, "action": "schedule", "chat_id": chat_id}

    if command in {"catalog", "products"}:
        send_picture_menu(telegram, chat_id)
        return {"ok": True, "action": "menu", "chat_id": chat_id}

    if command in {"product", "sheet"}:
        return _send_sheet(telegram, chat_id, _rest(text))

    if command == "order" or text.lower().startswith("order:"):
        detail = _rest(text) if command == "order" else text.split(":", 1)[1].strip()
        if not detail:
            send_picture_menu(telegram, chat_id)
            return {"ok": True, "action": "menu", "chat_id": chat_id}
        result = fire_reflex(
            "order",
            detail,
            exclude_chats={chat_id},
            require_destination=False,
        )
        telegram.send_message(chat_id, CUSTOMER_CONFIRM.format(detail=detail))
        product = _matched_product(detail)
        if product:
            telegram.send_document(
                chat_id,
                pdf_path(product),
                caption=format_product_caption(product),
            )
        return {
            "ok": True,
            "action": "order",
            "chat_id": chat_id,
            "detail": detail,
            "notified": result.status,
            "product": None if product is None else product["id"],
        }

    if text:
        telegram.send_message(
            chat_id,
            "Use the picture menu — tap This one on the vial you want.",
        )
        send_picture_menu(telegram, chat_id)
        return {"ok": True, "action": "menu", "chat_id": chat_id}

    return {"ok": True, "ignored": True, "bot": REQUIRED_USERNAME}
