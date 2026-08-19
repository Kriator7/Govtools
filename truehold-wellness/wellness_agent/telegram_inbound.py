"""Inbound Telegram for TrueHold Wellness: intro, quick menu, one tile, phone capture."""

from __future__ import annotations

from wellness_agent.access import PRIVILEGED_COMMANDS, STAFF_DENIED, is_operator
from wellness_agent.catalog import (
    UnknownProductError,
    find_product,
)
from wellness_agent.clients import (
    client_phone,
    parse_phone,
    phone_line_for_staff,
    save_client_phone,
)
from wellness_agent.compose import compose_alert, format_alert
from wellness_agent.greetings import is_salutation
from wellness_agent.identity import REQUIRED_USERNAME
from wellness_agent.inventory.build_brand import service_path
from wellness_agent.menu import (
    CUSTOMER_CONFIRM,
    PHONE_THANKS,
    TYPE_PHONE,
    _place_interest_order,
    ask_for_phone,
    complete_pending_order_if_ready,
    handle_menu_callback,
    parse_interest_qty,
    remove_keyboard,
    send_greet_again,
    send_host_photo,
    send_info_pdf,
    send_introduction_menu,
    send_quick_menu,
    send_theo_talk,
)
from wellness_agent.team import current_host, flavor_caption
from wellness_agent.models import AlertTrigger
from wellness_agent.reflex import fire_reflex
from wellness_agent.session_store import (
    awaiting_phone,
    begin_session,
    intro_pending,
    mark_intro_played,
    set_awaiting_phone,
)
from wellness_agent.telegram_copy import (
    BOT_COMMANDS,
    CUSTOMER_COMMANDS,
    CUSTOMER_HELP,
    HELP,
    SCHEDULE,
    STAFF_COMMANDS,
    STAFF_HELP,
    send_schedule,
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


def _ids(payload_message: dict) -> tuple[str, str, str, dict]:
    chat = payload_message.get("chat") or {}
    sender = payload_message.get("from") or {}
    return (
        str(chat.get("id") or ""),
        str(sender.get("id") or ""),
        str(chat.get("type") or "private"),
        sender,
    )


def _matched_product(detail: str):
    tokens = [part for part in detail.replace("/", " ").replace(",", " ").split() if len(part) >= 3]
    for token in (detail, *tokens):
        try:
            return find_product(token)
        except UnknownProductError:
            continue
    return None


def _sender_name(sender: dict) -> str:
    parts = [str(sender.get("first_name") or "").strip(), str(sender.get("last_name") or "").strip()]
    return " ".join(part for part in parts if part)


def _record_phone(telegram, chat_id: str, phone: str, *, source: str, sender: dict) -> dict:
    entry = save_client_phone(
        chat_id,
        phone,
        source=source,
        user_id=str(sender.get("id") or chat_id),
        name=_sender_name(sender),
        username=str(sender.get("username") or ""),
    )
    set_awaiting_phone(chat_id, False)
    telegram.send_message(
        chat_id,
        PHONE_THANKS.format(phone=entry["phone"]),
        reply_markup=remove_keyboard(),
    )
    pending = complete_pending_order_if_ready(telegram, chat_id)
    return {"ok": True, "action": "phone-saved", "chat_id": chat_id, "pending": pending}


def _send_introduction(telegram, chat_id: str) -> None:
    send_introduction_menu(telegram, chat_id)
    mark_intro_played(chat_id)


def _handle_promo(telegram, chat_id: str, staff_id: str, rest: str) -> dict:
    """Staff-only. Sales never run until a person approves the row."""
    from wellness_agent.knowledge import decide_promo, draft_promo, list_promos, seed_approved_knowledge

    seed_approved_knowledge()
    parts = rest.split(None, 1)
    action = (parts[0] if parts else "").lower()
    detail = parts[1].strip() if len(parts) > 1 else ""
    if action in {"", "list"}:
        rows = list_promos()
        if not rows:
            telegram.send_message(chat_id, "No promotions on file. /promo draft Headline | body")
            return {"ok": True, "action": "promo-list", "chat_id": chat_id, "count": 0}
        lines = ["Promotions (customer sees approved only):"]
        for row in rows[:20]:
            lines.append(f"#{row['id']} [{row['status']}] {row['headline']}")
        telegram.send_message(chat_id, "\n".join(lines))
        return {"ok": True, "action": "promo-list", "chat_id": chat_id, "count": len(rows)}
    if action == "draft":
        if "|" in detail:
            headline, body = [part.strip() for part in detail.split("|", 1)]
        else:
            headline, body = detail, detail
        if not headline:
            telegram.send_message(chat_id, "Usage: /promo draft Headline | body")
            return {"ok": False, "action": "promo-draft", "chat_id": chat_id}
        promo = draft_promo(headline, body, staff_id=staff_id)
        telegram.send_message(
            chat_id,
            f"Draft #{promo['id']} pending approval. Customers cannot see it yet.\n"
            f"/promo approve {promo['id']}",
        )
        return {"ok": True, "action": "promo-draft", "chat_id": chat_id, "id": promo["id"]}
    if action in {"approve", "reject", "expire"} and detail.isdigit():
        status = {"approve": "approved", "reject": "rejected", "expire": "expired"}[action]
        promo = decide_promo(int(detail), status=status, staff_id=staff_id)
        if promo is None:
            telegram.send_message(chat_id, f"No promotion #{detail}.")
            return {"ok": False, "action": "promo-miss", "chat_id": chat_id}
        telegram.send_message(chat_id, f"Promotion #{promo['id']} is now {promo['status']}.")
        return {"ok": True, "action": f"promo-{status}", "chat_id": chat_id, "id": promo["id"]}
    telegram.send_message(
        chat_id,
        "Usage:\n/promo list\n/promo draft Headline | body\n/promo approve <id>\n/promo reject <id>",
    )
    return {"ok": False, "action": "promo-help", "chat_id": chat_id}


def _send_sheet(telegram, chat_id: str, query: str) -> dict:
    if not query:
        telegram.send_message(chat_id, "Tap a name on /menu.")
        return {"ok": True, "action": "product-help", "chat_id": chat_id}
    try:
        product = find_product(query)
    except UnknownProductError as exc:
        telegram.send_message(chat_id, str(exc))
        return {"ok": False, "action": "product-miss", "chat_id": chat_id, "error": str(exc)}
    try:
        send_info_pdf(telegram, chat_id, product)
    except FileNotFoundError as exc:
        telegram.send_message(chat_id, str(exc))
        return {"ok": False, "action": "product-miss", "chat_id": chat_id, "error": str(exc)}
    return {"ok": True, "action": "product", "chat_id": chat_id, "product": product["id"]}


def handle_telegram_update(payload: dict, telegram) -> dict:
    callback = payload.get("callback_query")
    if callback:
        return handle_menu_callback(callback, telegram)

    message = payload.get("message") or {}
    text = str(message.get("text") or "").strip()
    chat_id, user_id, chat_type, sender = _ids(message)
    if not chat_id:
        return {"ok": True, "ignored": True}

    contact = message.get("contact") if isinstance(message.get("contact"), dict) else None
    if contact and contact.get("phone_number"):
        return _record_phone(
            telegram,
            chat_id,
            str(contact["phone_number"]),
            source="telegram_contact",
            sender=sender,
        )

    if text.lower() in {
        "i'll type my number",
        "ill type my number",
        "i will type my number",
        "✏️ type it",
        "type it",
    }:
        set_awaiting_phone(chat_id, True)
        telegram.send_message(chat_id, TYPE_PHONE)
        return {"ok": True, "action": "type-phone", "chat_id": chat_id}

    command = _command(text)
    staff = is_operator(user_id, chat_id, chat_type)

    looks_like_phone = bool(parse_phone(text)) and len(text) <= 22 and sum(ch.isdigit() for ch in text) >= 10
    if looks_like_phone and command not in PRIVILEGED_COMMANDS | {"start", "help", "menu", "schedule", "order"}:
        return _record_phone(telegram, chat_id, text, source="typed", sender=sender)

    if awaiting_phone(chat_id) and text and command not in PRIVILEGED_COMMANDS | {"start", "help", "menu", "schedule"}:
        if not (is_salutation(text) or is_salutation(command)):
            telegram.send_message(chat_id, TYPE_PHONE)
            return {"ok": True, "action": "type-phone", "chat_id": chat_id}

    if command in PRIVILEGED_COMMANDS:
        if command == "inbox" and staff:
            alert = compose_alert(AlertTrigger(type="business", headline="business inbox"))
            telegram.send_message(chat_id, format_alert(alert))
            return {"ok": True, "action": "inbox", "chat_id": chat_id, "staff": True}
        if command == "stock" and staff:
            from wellness_agent.stock import format_stock

            telegram.send_message(chat_id, format_stock())
            return {"ok": True, "action": "stock", "chat_id": chat_id, "staff": True}
        if command == "promo" and staff:
            return _handle_promo(telegram, chat_id, user_id, _rest(text))
        telegram.send_message(chat_id, STAFF_DENIED)
        return {"ok": False, "action": "staff-denied", "chat_id": chat_id}

    if command in {"start", "help", "menu"}:
        if command == "help":
            telegram.send_message(chat_id, STAFF_HELP if staff else CUSTOMER_HELP)
            return {"ok": True, "action": "help", "chat_id": chat_id, "staff": staff}
        if command == "start":
            begin_session(chat_id)
            if staff:
                telegram.send_message(chat_id, STAFF_HELP)
            _send_introduction(telegram, chat_id)
            return {"ok": True, "action": "intro", "chat_id": chat_id, "staff": staff}
        mark_intro_played(chat_id)
        send_quick_menu(telegram, chat_id)
        return {"ok": True, "action": "menu", "chat_id": chat_id, "staff": staff}

    if command == "schedule":
        send_schedule(telegram, chat_id)
        if not client_phone(chat_id):
            ask_for_phone(telegram, chat_id)
        return {"ok": True, "action": "schedule", "chat_id": chat_id}

    if command in {"catalog", "products"}:
        mark_intro_played(chat_id)
        send_quick_menu(telegram, chat_id)
        return {"ok": True, "action": "menu", "chat_id": chat_id}

    if command in {"product", "sheet"}:
        return _send_sheet(telegram, chat_id, _rest(text))

    if command == "order" or text.lower().startswith("order:"):
        detail = _rest(text) if command == "order" else text.split(":", 1)[1].strip()
        if not detail:
            mark_intro_played(chat_id)
            send_quick_menu(telegram, chat_id)
            return {"ok": True, "action": "menu", "chat_id": chat_id}
        product = _matched_product(detail)
        if product:
            return _place_interest_order(telegram, chat_id, product, parse_interest_qty(detail))
        staff_detail = f"{detail}\n{phone_line_for_staff(chat_id)}"
        result = fire_reflex(
            "order",
            staff_detail,
            exclude_chats={chat_id},
            require_destination=False,
        )
        host = current_host(chat_id)
        send_host_photo(
            telegram,
            chat_id,
            "cheer",
            flavor_caption(host, "cheer", CUSTOMER_CONFIRM.format(detail=detail)),
            host=host,
            effect=True,
        )
        if not client_phone(chat_id):
            ask_for_phone(telegram, chat_id)
        return {
            "ok": True,
            "action": "order",
            "chat_id": chat_id,
            "detail": detail,
            "notified": result.status,
            "product": None,
        }

    if text and (is_salutation(text) or is_salutation(command)):
        if intro_pending(chat_id):
            _send_introduction(telegram, chat_id)
            return {"ok": True, "action": "intro", "chat_id": chat_id}
        send_greet_again(telegram, chat_id, text)
        return {"ok": True, "action": "greet-again", "chat_id": chat_id}

    if text:
        if intro_pending(chat_id):
            _send_introduction(telegram, chat_id)
            return {"ok": True, "action": "intro", "chat_id": chat_id}
        source = send_theo_talk(telegram, chat_id, text)
        return {"ok": True, "action": "talk", "chat_id": chat_id, "source": source}

    return {"ok": True, "ignored": True, "bot": REQUIRED_USERNAME}
