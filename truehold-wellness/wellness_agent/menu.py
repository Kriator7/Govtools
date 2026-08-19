"""Quick menu then one product tile for TrueHold Wellness customers.

Hello sends a brand graphic plus a compact button list — not every SKU
photo. Tapping a name sends that tile. Phone is requested because Telegram
does not expose it unless the client shares contact
(https://core.telegram.org/bots/api#keyboardbutton).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wellness_agent.catalog import (
    UnknownProductError,
    find_product,
    format_product_caption,
    pdf_path,
    products,
)
from wellness_agent.clients import client_phone, phone_line_for_staff
from wellness_agent.inventory.build_brand import hero_path, service_path
from wellness_agent.inventory.build_cards import card_path, ensure_cards
from wellness_agent.reflex import fire_reflex
from wellness_agent.session_store import pending_order, set_awaiting_phone, set_pending_order
from wellness_agent.telegram_copy import CALL_AND_DOCS, INTRODUCTION, SERVICE_POLICY

MENU_INTRO = (
    "Quick menu — tap one name. We will send that tile.\n"
    f"{SERVICE_POLICY}\n"
    "Educational information only. "
    f"{CALL_AND_DOCS}."
)

CUSTOMER_CONFIRM = (
    f"Got it. The TrueHold team will call to confirm, consult, and complete required documentation.\n"
    "{detail}\n"
    f"{SERVICE_POLICY} Consult before payment. Educational only."
)

ASK_PHONE = (
    "Telegram cannot share your number unless you send it.\n"
    "Share your phone, or type it, so we can call to confirm, consult, "
    "and complete required documentation."
)

PHONE_THANKS = (
    "Thanks. We have {phone} on file and will call to confirm, consult, "
    "and complete required documentation."
)

TYPE_PHONE = "Reply with your mobile number, including area code. Example: 702-555-0100"

NEED_PHONE = (
    "We still need a phone number so the team can call to confirm, consult, "
    "and complete required documentation."
)


def _button(text: str, data: str) -> dict[str, str]:
    return {"text": text, "callback_data": data}


def _keyboard(rows: list[list[dict[str, str]]]) -> dict[str, Any]:
    return {"inline_keyboard": rows}


def contact_keyboard() -> dict[str, Any]:
    """Reply keyboard: request_contact. https://core.telegram.org/bots/api#keyboardbutton"""
    return {
        "keyboard": [
            [{"text": "Share my phone number", "request_contact": True}],
            [{"text": "I'll type my number"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def remove_keyboard() -> dict[str, Any]:
    return {"remove_keyboard": True}


def quick_menu_keyboard() -> dict[str, Any]:
    items = products()
    rows: list[list[dict[str, str]]] = []
    row: list[dict[str, str]] = []
    for item in items:
        row.append(_button(item["name"], f"w:tile:{item['id']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_button("Talk to the team", "w:team")])
    return _keyboard(rows)


def after_pick_keyboard(product_id: str) -> dict[str, Any]:
    return _keyboard(
        [
            [_button("Order this", f"w:qty:{product_id}")],
            [_button("See info sheet", f"w:info:{product_id}")],
            [_button("See menu", "w:menu")],
        ]
    )


def qty_keyboard(product_id: str) -> dict[str, Any]:
    return _keyboard(
        [
            [
                _button("1 vial", f"w:ask:{product_id}:1"),
                _button("2 vials", f"w:ask:{product_id}:2"),
                _button("3 vials", f"w:ask:{product_id}:3"),
            ],
            [_button("Talk to the team", "w:team")],
            [_button("See menu", "w:menu")],
        ]
    )


def confirm_keyboard(product_id: str, qty: str) -> dict[str, Any]:
    return _keyboard(
        [
            [_button("Yes — Las Vegas resident", f"w:yes:{product_id}:{qty}")],
            [_button("Not in Las Vegas", "w:team")],
            [_button("Pick something else", "w:menu")],
        ]
    )


def send_brand_photo(
    telegram,
    chat_id: str,
    path: Path,
    caption: str,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    if hasattr(telegram, "send_photo"):
        telegram.send_photo(chat_id, path, caption=caption, reply_markup=reply_markup)
        return
    telegram.send_message(chat_id, caption, reply_markup=reply_markup)


def send_introduction_menu(telegram, chat_id: str) -> None:
    send_brand_photo(telegram, chat_id, hero_path(), INTRODUCTION, quick_menu_keyboard())


def send_quick_menu(telegram, chat_id: str, *, include_blurb: bool = True) -> None:
    caption = MENU_INTRO if include_blurb else "Tap one name:"
    send_brand_photo(telegram, chat_id, hero_path(), caption, quick_menu_keyboard())


def send_picture_menu(telegram, chat_id: str, *, include_blurb: bool = True) -> int:
    """Back-compat name: compact menu, not one photo per SKU."""
    send_quick_menu(telegram, chat_id, include_blurb=include_blurb)
    return len(products())


def send_product_tile(telegram, chat_id: str, product: dict) -> None:
    ensure_cards()
    path = card_path(product)
    caption = (
        f"{product['name']}\n{product['vial']}\n"
        f"{SERVICE_POLICY}\n"
        "Order this, see the info sheet, or go back to the menu."
    )
    send_brand_photo(telegram, chat_id, path, caption, after_pick_keyboard(product["id"]))


def ask_for_phone(telegram, chat_id: str, *, extra: str | None = None) -> None:
    set_awaiting_phone(chat_id, True)
    caption = ASK_PHONE if not extra else f"{extra}\n\n{ASK_PHONE}"
    send_brand_photo(telegram, chat_id, service_path(), caption, contact_keyboard())


def _place_interest_order(telegram, chat_id: str, product: dict, qty: str) -> dict[str, Any]:
    if not client_phone(chat_id):
        set_pending_order(chat_id, product["id"], qty)
        ask_for_phone(telegram, chat_id, extra=NEED_PHONE)
        return {
            "ok": True,
            "action": "need-phone",
            "chat_id": str(chat_id),
            "product": product["id"],
            "qty": qty,
        }
    detail = f"{qty}x {product['name']} ({product['vial']})"
    staff_detail = f"{detail}\n{phone_line_for_staff(chat_id)}"
    result = fire_reflex(
        "order",
        f"Telegram interest order: {staff_detail}",
        exclude_chats={str(chat_id)},
        require_destination=False,
    )
    set_pending_order(chat_id, None, None)
    send_brand_photo(
        telegram,
        chat_id,
        service_path(),
        CUSTOMER_CONFIRM.format(detail=detail),
    )
    try:
        telegram.send_document(
            chat_id,
            pdf_path(product),
            caption=format_product_caption(product),
        )
    except FileNotFoundError:
        pass
    return {
        "ok": True,
        "action": "order-confirm",
        "chat_id": str(chat_id),
        "product": product["id"],
        "qty": qty,
        "notified": result.status,
    }


def complete_pending_order_if_ready(telegram, chat_id: str) -> dict[str, Any] | None:
    pending = pending_order(chat_id)
    if not pending or not client_phone(chat_id):
        return None
    try:
        product = find_product(str(pending.get("product_id") or ""))
    except UnknownProductError:
        set_pending_order(chat_id, None, None)
        return None
    qty = str(pending.get("qty") or "")
    if qty not in {"1", "2", "3"}:
        set_pending_order(chat_id, None, None)
        return None
    return _place_interest_order(telegram, chat_id, product, qty)


def handle_menu_callback(query: dict[str, Any], telegram) -> dict[str, Any]:
    callback_id = str(query.get("id") or "")
    data = str(query.get("data") or "")
    message = query.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    if hasattr(telegram, "answer_callback_query") and callback_id:
        telegram.answer_callback_query(callback_id)
    if not chat_id:
        return {"ok": True, "ignored": True, "action": "callback-no-chat"}
    parts = data.split(":")
    if len(parts) < 2 or parts[0] != "w":
        return {"ok": True, "ignored": True, "action": "callback-unknown"}
    action = parts[1]
    sku = parts[2] if len(parts) > 2 else ""
    qty = parts[3] if len(parts) > 3 else ""
    if action == "menu":
        send_quick_menu(telegram, chat_id)
        return {"ok": True, "action": "menu", "chat_id": chat_id}
    if action == "team":
        from wellness_agent.telegram_copy import SCHEDULE, schedule_keyboard

        telegram.send_message(chat_id, SCHEDULE, reply_markup=schedule_keyboard())
        return {"ok": True, "action": "schedule", "chat_id": chat_id}
    try:
        product = find_product(sku) if sku else None
    except UnknownProductError as exc:
        telegram.send_message(chat_id, str(exc))
        return {"ok": False, "action": "callback-miss", "chat_id": chat_id}
    if product is None:
        return {"ok": True, "ignored": True, "action": "callback-unknown"}
    if action in {"pick", "tile"}:
        send_product_tile(telegram, chat_id, product)
        return {"ok": True, "action": "tile", "chat_id": chat_id, "product": product["id"]}
    if action == "info":
        telegram.send_document(
            chat_id,
            pdf_path(product),
            caption=format_product_caption(product),
        )
        telegram.send_message(
            chat_id,
            "Want this dry vial, or pick a different name?",
            reply_markup=after_pick_keyboard(product["id"]),
        )
        return {"ok": True, "action": "info", "chat_id": chat_id, "product": product["id"]}
    if action == "qty":
        send_brand_photo(
            telegram,
            chat_id,
            service_path(),
            f"How many {product['name']} dry vials?\n"
            "Interest order only. "
            f"{SERVICE_POLICY} {CALL_AND_DOCS}.",
            qty_keyboard(product["id"]),
        )
        return {"ok": True, "action": "qty", "chat_id": chat_id, "product": product["id"]}
    if action == "ask" and qty in {"1", "2", "3"}:
        send_brand_photo(
            telegram,
            chat_id,
            service_path(),
            f"Send this interest order to the TrueHold team?\n"
            f"{qty}x {product['name']} ({product['vial']})\n"
            f"{SERVICE_POLICY}\n"
            f"{CALL_AND_DOCS}. Confirm only if you are a Las Vegas resident.",
            confirm_keyboard(product["id"], qty),
        )
        return {
            "ok": True,
            "action": "ask",
            "chat_id": chat_id,
            "product": product["id"],
            "qty": qty,
        }
    if action == "yes" and qty in {"1", "2", "3"}:
        return _place_interest_order(telegram, chat_id, product, qty)
    return {"ok": True, "ignored": True, "action": "callback-unknown"}
