"""Picture-menu order flow for TrueHold Wellness customers.

One photo per SKU with a single This one button, then quantity, then confirm.
Inline keyboards: https://core.telegram.org/bots/api#inlinekeyboardmarkup
sendPhoto: https://core.telegram.org/bots/api#sendphoto
answerCallbackQuery: https://core.telegram.org/bots/api#answercallbackquery
"""

from __future__ import annotations

import os
import time
from typing import Any

from wellness_agent.catalog import (
    UnknownProductError,
    find_product,
    format_product_caption,
    pdf_path,
    products,
)
from wellness_agent.inventory.build_cards import card_path, ensure_cards
from wellness_agent.reflex import fire_reflex

MENU_INTRO = (
    "TrueHold Wellness picture menu\n"
    "Scroll the photos. Tap This one on the vial you want.\n"
    "Las Vegas residents only. Educational information only. "
    "The team confirms before any payment."
)

CUSTOMER_CONFIRM = (
    "Got it. The TrueHold team will confirm this interest order.\n"
    "{detail}\n"
    "Las Vegas residents only. Consult before payment. Educational only."
)


def _button(text: str, data: str) -> dict[str, str]:
    return {"text": text, "callback_data": data}


def _keyboard(rows: list[list[dict[str, str]]]) -> dict[str, Any]:
    return {"inline_keyboard": rows}


def product_keyboard(product_id: str) -> dict[str, Any]:
    return _keyboard([[_button("This one", f"w:pick:{product_id}")]])


def after_pick_keyboard(product_id: str) -> dict[str, Any]:
    return _keyboard(
        [
            [_button("Order this", f"w:qty:{product_id}")],
            [_button("See info sheet", f"w:info:{product_id}")],
            [_button("See all photos", "w:menu")],
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
            [_button("See all photos", "w:menu")],
        ]
    )


def confirm_keyboard(product_id: str, qty: str) -> dict[str, Any]:
    return _keyboard(
        [
            [_button("Yes, send to the team", f"w:yes:{product_id}:{qty}")],
            [_button("Pick something else", "w:menu")],
        ]
    )


def send_picture_menu(telegram, chat_id: str) -> int:
    ensure_cards()
    telegram.send_message(chat_id, MENU_INTRO)
    count = 0
    live = os.environ.get("TELEGRAM_MODE", "mock") == "live"
    for item in products():
        path = card_path(item)
        caption = f"{item['name']}\n{item['vial']}\nTap This one if this is the vial you want."
        if hasattr(telegram, "send_photo"):
            telegram.send_photo(
                chat_id,
                path,
                caption=caption,
                reply_markup=product_keyboard(item["id"]),
            )
        else:
            telegram.send_message(
                chat_id,
                caption,
                reply_markup=product_keyboard(item["id"]),
            )
        count += 1
        if live:
            time.sleep(0.35)
    return count


def _place_interest_order(telegram, chat_id: str, product: dict, qty: str) -> dict[str, Any]:
    detail = f"{qty}x {product['name']} ({product['vial']})"
    result = fire_reflex(
        "order",
        f"Telegram picture-menu interest order: {detail}",
        exclude_chats={str(chat_id)},
        require_destination=False,
    )
    telegram.send_message(chat_id, CUSTOMER_CONFIRM.format(detail=detail))
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
        send_picture_menu(telegram, chat_id)
        return {"ok": True, "action": "menu", "chat_id": chat_id}
    if action == "team":
        from wellness_agent.telegram_copy import SCHEDULE

        telegram.send_message(chat_id, SCHEDULE)
        return {"ok": True, "action": "schedule", "chat_id": chat_id}
    try:
        product = find_product(sku) if sku else None
    except UnknownProductError as exc:
        telegram.send_message(chat_id, str(exc))
        return {"ok": False, "action": "callback-miss", "chat_id": chat_id}
    if product is None:
        return {"ok": True, "ignored": True, "action": "callback-unknown"}
    if action == "pick":
        telegram.send_message(
            chat_id,
            f"{product['name']} — {product['vial']}\n"
            "One tap: order this, see the info sheet, or look at the other photos.",
            reply_markup=after_pick_keyboard(product["id"]),
        )
        return {"ok": True, "action": "pick", "chat_id": chat_id, "product": product["id"]}
    if action == "info":
        telegram.send_document(
            chat_id,
            pdf_path(product),
            caption=format_product_caption(product),
        )
        telegram.send_message(
            chat_id,
            "Want this vial, or pick a different photo?",
            reply_markup=after_pick_keyboard(product["id"]),
        )
        return {"ok": True, "action": "info", "chat_id": chat_id, "product": product["id"]}
    if action == "qty":
        telegram.send_message(
            chat_id,
            f"How many {product['name']} vials? Interest order only — the team confirms before payment.",
            reply_markup=qty_keyboard(product["id"]),
        )
        return {"ok": True, "action": "qty", "chat_id": chat_id, "product": product["id"]}
    if action == "ask" and qty in {"1", "2", "3"}:
        telegram.send_message(
            chat_id,
            f"Send this interest order to the TrueHold team?\n{qty}x {product['name']} ({product['vial']})",
            reply_markup=confirm_keyboard(product["id"], qty),
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
