"""Quick menu then one product tile for TrueHold Wellness customers.

Hello sends a brand graphic plus a compact button list — not every SKU
photo. Tapping a name sends that tile. Phone is requested because Telegram
does not expose it unless the client shares contact
(https://core.telegram.org/bots/api#keyboardbutton).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from wellness_agent.catalog import (
    UnknownProductError,
    find_product,
    format_product_caption,
    locked_sheet_filename,
    telegram_file_path,
    products,
)
from wellness_agent.clients import client_phone, phone_line_for_staff
from wellness_agent.inventory.build_brand import hero_path, logo_path, service_path
from wellness_agent.inventory.build_cards import card_path, ensure_cards
from wellness_agent.reflex import fire_reflex
from wellness_agent.session_store import pending_order, set_awaiting_phone, set_pending_order
from wellness_agent.stock import record_order_row, staff_inventory_line
from wellness_agent.telegram_copy import (
    CALL_AND_DOCS,
    CELEBRATE_EFFECT_ID,
    INTRODUCTION,
    PARSE_MODE,
)

MENU_INTRO = (
    "<b>Menu</b>\n"
    "Tap a name — one picture, short buttons.\n"
    "Las Vegas · dry vials only"
)

CUSTOMER_CONFIRM = (
    "<b>You're in 🎉</b>\n"
    "{detail}\n"
    "\n"
    "<b>Next</b>\n"
    "The team calls to confirm, consult, and complete required documentation.\n"
    "\n"
    "Las Vegas · dry vials only · educational only\n"
    "Zelle on the call · debit via Team"
)

ASK_PHONE = (
    "<b>Phone</b>\n"
    "Telegram cannot share your number unless you send it.\n"
    "Share it, or type it, so we can call to confirm, consult, "
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

PRODUCT_EMOJI = {
    "tirzepatide": "💉",
    "retatrutide": "🔥",
    "semax": "🧠",
    "nad": "⚡",
    "klow": "🌿",
    "mots-c": "🔋",
    "ss-31": "💎",
    "ghk-cu": "✨",
}

TOASTS = {
    "yes": "You're in 🎉",
    "prep": "Prep 🛠️",
}


def _button(text: str, data: str) -> dict[str, str]:
    return {"text": text, "callback_data": data}


def _keyboard(rows: list[list[dict[str, str]]]) -> dict[str, Any]:
    return {"inline_keyboard": rows}


def _product_button(item: dict[str, Any]) -> dict[str, str]:
    emoji = PRODUCT_EMOJI.get(item["id"], "•")
    return _button(f"{emoji} {item['name']}", f"w:tile:{item['id']}")


def contact_keyboard() -> dict[str, Any]:
    """Reply keyboard: request_contact. https://core.telegram.org/bots/api#keyboardbutton"""
    return {
        "keyboard": [
            [{"text": "📱 Share my phone", "request_contact": True}],
            [{"text": "✏️ Type it"}],
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
        row.append(_product_button(item))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_button("🛠️ Prep", "w:prep"), _button("📅 Team", "w:team")])
    return _keyboard(rows)


def after_pick_keyboard(product_id: str) -> dict[str, Any]:
    return _keyboard(
        [
            [_button("🛒 Order", f"w:qty:{product_id}"), _button("📄 Sheet", f"w:info:{product_id}")],
            [_button("🛠️ Prep", f"w:prep:{product_id}"), _button("📅 Team", "w:team")],
            [_button("⬅️ Menu", "w:menu")],
        ]
    )


def info_sheet_keyboard(product_id: str) -> dict[str, Any]:
    """No URL buttons — a shop URL here lands in Telegram Links instead of Files."""
    return _keyboard(
        [
            [_button("🛒 Order", f"w:qty:{product_id}"), _button("🛠️ Prep", f"w:prep:{product_id}")],
            [_button("📅 Team", "w:team"), _button("⬅️ Menu", "w:menu")],
        ]
    )


def qty_keyboard(product_id: str) -> dict[str, Any]:
    return _keyboard(
        [
            [
                _button("1", f"w:ask:{product_id}:1"),
                _button("2", f"w:ask:{product_id}:2"),
                _button("3", f"w:ask:{product_id}:3"),
            ],
            [_button("📅 Team", "w:team"), _button("⬅️ Menu", "w:menu")],
        ]
    )


def confirm_keyboard(product_id: str, qty: str) -> dict[str, Any]:
    return _keyboard(
        [
            [_button("✅ Vegas", f"w:yes:{product_id}:{qty}"), _button("📍 Not LV", "w:team")],
            [_button("⬅️ Menu", "w:menu")],
        ]
    )


def send_brand_photo(
    telegram,
    chat_id: str,
    path: Path,
    caption: str,
    reply_markup: dict[str, Any] | None = None,
    *,
    parse_mode: str | None = PARSE_MODE,
    message_effect_id: str | None = None,
) -> None:
    if hasattr(telegram, "send_photo"):
        try:
            telegram.send_photo(
                chat_id,
                path,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                message_effect_id=message_effect_id,
            )
            return
        except TypeError:
            telegram.send_photo(chat_id, path, caption=caption, reply_markup=reply_markup)
            return
    telegram.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode=parse_mode)


def parse_interest_qty(detail: str) -> str:
    text = str(detail or "").strip()
    match = re.search(r"\b([1-3])\s*x\b", text, flags=re.I)
    if match:
        return match.group(1)
    match = re.match(r"([1-3])\b", text)
    if match:
        return match.group(1)
    return "1"


def send_introduction_menu(telegram, chat_id: str) -> None:
    send_brand_photo(telegram, chat_id, logo_path(), INTRODUCTION, quick_menu_keyboard())


def send_quick_menu(telegram, chat_id: str, *, include_blurb: bool = True) -> None:
    caption = MENU_INTRO if include_blurb else "<b>Menu</b>\nTap a name:"
    send_brand_photo(telegram, chat_id, hero_path(), caption, quick_menu_keyboard())


def send_picture_menu(telegram, chat_id: str, *, include_blurb: bool = True) -> int:
    """Back-compat name: compact menu, not one photo per SKU."""
    send_quick_menu(telegram, chat_id, include_blurb=include_blurb)
    return len(products())


def send_product_tile(telegram, chat_id: str, product: dict) -> None:
    from html import escape

    ensure_cards()
    path = card_path(product)
    caption = (
        f"<b>{escape(str(product['name']))}</b>\n"
        f"{escape(str(product['vial']))}\n"
        "\n"
        "<b>Prep</b> Las Vegas · dry vials only\n"
        "Tap a button — Order, Sheet, Prep, or Team."
    )
    send_brand_photo(telegram, chat_id, path, caption, after_pick_keyboard(product["id"]))


def send_prep_card(telegram, chat_id: str, product: dict | None = None) -> None:
    """Prep policy only. Mix and dosing stay on the locked PDF, not in chat."""
    from html import escape

    if product:
        heading = f"<b>🛠️ Prep</b> · {escape(str(product['name']))}"
        vial = escape(str(product["vial"]))
        extra = f"{vial}\nMix and starting amounts are on the locked sheet — tap Sheet."
        markup = after_pick_keyboard(product["id"])
    else:
        heading = "<b>🛠️ Prep</b>"
        extra = "Tap a name, then Sheet, for that vial’s locked information sheet."
        markup = quick_menu_keyboard()
    caption = (
        f"{heading}\n"
        "\n"
        "Las Vegas residents only\n"
        "Dry vials only — we do not ship mixed product\n"
        f"{CALL_AND_DOCS}.\n"
        "\n"
        f"{extra}"
    )
    send_brand_photo(telegram, chat_id, service_path(), caption, markup)


def send_info_pdf(telegram, chat_id: str, product: dict) -> None:
    caption = format_product_caption(product)
    path = telegram_file_path(product)
    filename = locked_sheet_filename(product)
    markup = info_sheet_keyboard(product["id"])
    if hasattr(telegram, "send_document"):
        try:
            telegram.send_document(
                chat_id,
                path,
                caption=caption,
                reply_markup=markup,
                filename=filename,
                parse_mode=PARSE_MODE,
            )
            return
        except TypeError:
            try:
                telegram.send_document(
                    chat_id,
                    path,
                    caption=caption,
                    reply_markup=markup,
                    filename=filename,
                )
                return
            except TypeError:
                telegram.send_document(chat_id, path, caption=caption)
                return
    telegram.send_message(chat_id, caption, reply_markup=markup, parse_mode=PARSE_MODE)


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
    inventory_line = staff_inventory_line(
        product["id"],
        int(qty),
        reason="telegram-interest-order",
        detail=f"chat {chat_id} {detail}",
    )
    try:
        record_order_row(
            product,
            qty,
            chat_id=str(chat_id),
            phone=client_phone(chat_id),
        )
    except Exception as exc:
        inventory_line = f"{inventory_line} Workbook update skipped: {exc}."
    staff_detail = f"{detail}\n{phone_line_for_staff(chat_id)}\n{inventory_line}"
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
        after_pick_keyboard(product["id"]),
        message_effect_id=CELEBRATE_EFFECT_ID,
    )
    try:
        send_info_pdf(telegram, chat_id, product)
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
    parts = data.split(":")
    action = parts[1] if len(parts) >= 2 else ""
    if hasattr(telegram, "answer_callback_query") and callback_id:
        telegram.answer_callback_query(callback_id, text=TOASTS.get(action))
    if not chat_id:
        return {"ok": True, "ignored": True, "action": "callback-no-chat"}
    if len(parts) < 2 or parts[0] != "w":
        return {"ok": True, "ignored": True, "action": "callback-unknown"}
    sku = parts[2] if len(parts) > 2 else ""
    qty = parts[3] if len(parts) > 3 else ""
    if action == "menu":
        send_quick_menu(telegram, chat_id)
        return {"ok": True, "action": "menu", "chat_id": chat_id}
    if action == "team":
        from wellness_agent.telegram_copy import send_schedule

        send_schedule(telegram, chat_id)
        return {"ok": True, "action": "schedule", "chat_id": chat_id}
    if action == "prep" and not sku:
        send_prep_card(telegram, chat_id)
        return {"ok": True, "action": "prep", "chat_id": chat_id}
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
        send_info_pdf(telegram, chat_id, product)
        return {"ok": True, "action": "info", "chat_id": chat_id, "product": product["id"]}
    if action == "prep":
        send_prep_card(telegram, chat_id, product)
        return {"ok": True, "action": "prep", "chat_id": chat_id, "product": product["id"]}
    if action == "qty":
        from html import escape

        send_brand_photo(
            telegram,
            chat_id,
            service_path(),
            f"<b>How many?</b>\n"
            f"{escape(str(product['name']))} · dry vials\n"
            "\n"
            "Las Vegas · we call to complete docs",
            qty_keyboard(product["id"]),
        )
        return {"ok": True, "action": "qty", "chat_id": chat_id, "product": product["id"]}
    if action == "ask" and qty in {"1", "2", "3"}:
        from html import escape

        send_brand_photo(
            telegram,
            chat_id,
            service_path(),
            f"<b>Confirm</b>\n"
            f"{escape(qty)}× {escape(str(product['name']))}\n"
            f"{escape(str(product['vial']))}\n"
            "\n"
            "Las Vegas residents only\n"
            f"{CALL_AND_DOCS}.",
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
