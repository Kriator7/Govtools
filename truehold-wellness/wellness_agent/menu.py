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
from wellness_agent.inventory.build_agent import agent_path, crew_path, ensure_host
from wellness_agent.inventory.build_brand import logo_path, service_path
from wellness_agent.inventory.build_cards import card_path, ensure_cards
from wellness_agent.reflex import fire_reflex
from wellness_agent.session_store import pending_order, set_awaiting_phone, set_pending_order
from wellness_agent.stock import record_order_row, staff_inventory_line
from wellness_agent.team import (
    advance_on_greet,
    button_label,
    button_style,
    current_host,
    effect_id,
    favorite_id,
    flavor_caption,
    members,
    pose_line,
    rotate_again,
    set_favorite,
    skip_to_next,
    tour_complete,
)
from wellness_agent.telegram_copy import (
    CALL_AND_DOCS,
    CELEBRATE_EFFECT_ID,
    INTRODUCTION,
    PARSE_MODE,
)

MENU_INTRO = (
    "<b>Menu</b>\n"
    "Tap a name — one picture, short buttons.\n"
    "We care that you get well. Your body, your call.\n"
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
    "crew": "The crew 📸",
    "fav": "Favorite locked",
    "next": "Next teammate",
    "rotate": "Tour reset",
    "set": "Favorite locked",
    "pick": "Pick a favorite",
}


def _button(text: str, data: str, *, style: str | None = None) -> dict[str, Any]:
    """Inline callback button. style: primary (blue), success (green), danger (red).

    https://core.telegram.org/bots/api#inlinekeyboardbutton
    """
    payload: dict[str, Any] = {"text": text, "callback_data": data}
    if style in {"primary", "success", "danger"}:
        payload["style"] = style
    return payload


def _keyboard(rows: list[list[dict[str, Any]]]) -> dict[str, Any]:
    return {"inline_keyboard": rows}


def _product_button(item: dict[str, Any], *, style: str | None = None) -> dict[str, Any]:
    emoji = PRODUCT_EMOJI.get(item["id"], "•")
    return _button(f"{emoji} {item['name']}", f"w:tile:{item['id']}", style=style)


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


def host_action_rows(chat_id: str, host: dict[str, Any] | None = None) -> list[list[dict[str, Any]]]:
    host = host or current_host(chat_id)
    tone = button_style(host)
    fav = favorite_id(chat_id)
    rows: list[list[dict[str, Any]]] = []
    if fav == host["id"]:
        rows.append([_button(f"✅ {host['icon']} {host['name']} is yours", "w:host:pick", style=tone)])
    else:
        pair = [_button(f"{host['icon']} Favorite {host['name']}", "w:host:fav", style=tone)]
        if not fav:
            pair.append(_button(button_label(host, "next"), "w:host:next", style=tone))
        rows.append(pair)
    if tour_complete(chat_id) and not fav:
        rows.append(
            [
                _button(button_label(host, "rotate"), "w:host:rotate", style=tone),
                _button(button_label(host, "pick"), "w:host:pick", style=tone),
            ]
        )
    return rows


def pick_host_keyboard(host: dict[str, Any] | None = None) -> dict[str, Any]:
    rows: list[list[dict[str, Any]]] = []
    row: list[dict[str, Any]] = []
    for item in members():
        row.append(
            _button(
                f"{item['icon']} {item['name']}",
                f"w:host:set:{item['id']}",
                style=button_style(item),
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_button(button_label(host, "menu"), "w:menu", style=button_style(host))])
    return _keyboard(rows)


def quick_menu_keyboard(chat_id: str | None = None, host: dict[str, Any] | None = None) -> dict[str, Any]:
    host = host or (current_host(chat_id) if chat_id else None)
    tone = button_style(host)
    items = products()
    rows: list[list[dict[str, Any]]] = []
    row: list[dict[str, Any]] = []
    for item in items:
        row.append(_product_button(item, style=tone))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    if chat_id:
        rows.extend(host_action_rows(str(chat_id), host))
    rows.append(
        [
            _button(button_label(host, "prep"), "w:prep", style=tone),
            _button(button_label(host, "team"), "w:team", style=tone),
            _button(button_label(host, "crew"), "w:crew", style=tone),
        ]
    )
    return _keyboard(rows)


def after_pick_keyboard(product_id: str, host: dict[str, Any] | None = None) -> dict[str, Any]:
    tone = button_style(host)
    return _keyboard(
        [
            [
                _button(button_label(host, "order"), f"w:qty:{product_id}", style="success"),
                _button(button_label(host, "sheet"), f"w:info:{product_id}", style=tone),
            ],
            [
                _button(button_label(host, "prep"), f"w:prep:{product_id}", style=tone),
                _button(button_label(host, "team"), "w:team", style=tone),
            ],
            [_button(button_label(host, "menu"), "w:menu", style=tone)],
        ]
    )


def info_sheet_keyboard(product_id: str, host: dict[str, Any] | None = None) -> dict[str, Any]:
    """No URL buttons — a shop URL here lands in Telegram Links instead of Files."""
    tone = button_style(host)
    return _keyboard(
        [
            [
                _button(button_label(host, "order"), f"w:qty:{product_id}", style="success"),
                _button(button_label(host, "prep"), f"w:prep:{product_id}", style=tone),
            ],
            [
                _button(button_label(host, "team"), "w:team", style=tone),
                _button(button_label(host, "menu"), "w:menu", style=tone),
            ],
        ]
    )


def qty_keyboard(product_id: str, host: dict[str, Any] | None = None) -> dict[str, Any]:
    tone = button_style(host)
    return _keyboard(
        [
            [
                _button(button_label(host, "qty1"), f"w:ask:{product_id}:1", style=tone),
                _button(button_label(host, "qty2"), f"w:ask:{product_id}:2", style=tone),
                _button(button_label(host, "qty3"), f"w:ask:{product_id}:3", style=tone),
            ],
            [
                _button(button_label(host, "team"), "w:team", style=tone),
                _button(button_label(host, "menu"), "w:menu", style=tone),
            ],
        ]
    )


def confirm_keyboard(product_id: str, qty: str, host: dict[str, Any] | None = None) -> dict[str, Any]:
    tone = button_style(host)
    return _keyboard(
        [
            [
                _button(button_label(host, "vegas"), f"w:yes:{product_id}:{qty}", style="success"),
                _button(button_label(host, "not_lv"), "w:team", style="danger"),
            ],
            [_button(button_label(host, "menu"), "w:menu", style=tone)],
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


def send_host_photo(
    telegram,
    chat_id: str,
    pose: str,
    caption: str,
    reply_markup: dict[str, Any] | None = None,
    *,
    host: dict[str, Any] | None = None,
    effect: bool = False,
) -> dict[str, Any]:
    host = host or current_host(chat_id)
    ensure_host(host["id"])
    send_brand_photo(
        telegram,
        chat_id,
        agent_path(pose, host["id"]),
        caption,
        reply_markup,
        message_effect_id=effect_id(host) if effect else None,
    )
    return host


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
    send_brand_photo(telegram, chat_id, logo_path(), INTRODUCTION, quick_menu_keyboard(str(chat_id)))


def send_greet_again(telegram, chat_id: str, text: str = "hi") -> None:
    from wellness_agent.knowledge.talk import reply

    host = advance_on_greet(chat_id)
    spoken = reply(text, chat_id=str(chat_id), greet=True, host=host)
    caption = spoken.text
    if tour_complete(chat_id) and not favorite_id(chat_id):
        caption = (
            f"{caption}\n\n"
            "<b>You have met the whole floor team.</b>\n"
            "Rotate again, or pick a favorite who always serves you."
        )
    send_host_photo(
        telegram,
        chat_id,
        spoken.pose,
        caption,
        quick_menu_keyboard(str(chat_id), host),
        host=host,
        effect=True,
    )


def send_theo_talk(telegram, chat_id: str, text: str) -> str:
    from wellness_agent.knowledge.talk import reply

    host = current_host(chat_id)
    spoken = reply(text, chat_id=str(chat_id), greet=False, host=host)
    send_host_photo(
        telegram,
        chat_id,
        spoken.pose,
        spoken.text,
        quick_menu_keyboard(str(chat_id), host),
        host=host,
    )
    return spoken.source


CREW_CAPTION = (
    "<b>The floor crew</b>\n"
    "TrueHold Wellness · Las Vegas\n"
    "Bunny ears, one happy closed-eye laugh, the floor team who care that you get well.\n"
    "Take ownership. Tell others if this house helped.\n"
    "Tap a name — or lock a favorite who always serves you."
)


def send_crew_photo(telegram, chat_id: str) -> None:
    send_brand_photo(
        telegram,
        chat_id,
        crew_path(),
        CREW_CAPTION,
        quick_menu_keyboard(str(chat_id)),
        message_effect_id=CELEBRATE_EFFECT_ID,
    )


def send_quick_menu(telegram, chat_id: str, *, include_blurb: bool = True) -> None:
    host = current_host(chat_id)
    extra = MENU_INTRO if include_blurb else "<b>Menu</b>\nTap a name:"
    send_host_photo(
        telegram,
        chat_id,
        "present",
        flavor_caption(host, "present", extra),
        quick_menu_keyboard(str(chat_id), host),
        host=host,
    )


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
    send_brand_photo(
        telegram, chat_id, path, caption, after_pick_keyboard(product["id"], current_host(chat_id))
    )


def send_prep_card(telegram, chat_id: str, product: dict | None = None) -> None:
    """Prep policy only. Mix and dosing stay on the locked PDF, not in chat."""
    from html import escape

    if product:
        heading = f"<b>🛠️ Prep</b> · {escape(str(product['name']))}"
        vial = escape(str(product["vial"]))
        extra = f"{vial}\nMix and starting amounts are on the locked sheet — tap Sheet."
        markup = after_pick_keyboard(product["id"], current_host(chat_id))
    else:
        heading = "<b>🛠️ Prep</b>"
        extra = "Tap a name, then Sheet, for that vial’s locked information sheet."
        markup = quick_menu_keyboard(str(chat_id))
    caption = (
        f"{heading}\n"
        "\n"
        "Las Vegas residents only\n"
        "Dry vials only — we do not ship mixed product\n"
        f"{CALL_AND_DOCS}.\n"
        "\n"
        f"{extra}"
    )
    host = current_host(chat_id)
    send_host_photo(
        telegram,
        chat_id,
        "think",
        flavor_caption(host, "think", caption),
        markup,
        host=host,
    )


def send_team_card(telegram, chat_id: str) -> None:
    from wellness_agent.telegram_copy import SCHEDULE, schedule_keyboard

    host = current_host(chat_id)
    send_host_photo(
        telegram,
        chat_id,
        "soon",
        flavor_caption(host, "soon", SCHEDULE),
        schedule_keyboard(style=button_style(host), host=host),
        host=host,
    )


def send_info_pdf(telegram, chat_id: str, product: dict) -> None:
    from wellness_agent.sheet_store import remember_sheet_message, replace_prior_sheet

    caption = format_product_caption(product)
    path = telegram_file_path(product)
    filename = locked_sheet_filename(product)
    markup = info_sheet_keyboard(product["id"], current_host(chat_id))
    replace_prior_sheet(telegram, str(chat_id), product["id"])
    result = None
    if hasattr(telegram, "send_document"):
        try:
            result = telegram.send_document(
                chat_id,
                path,
                caption=caption,
                reply_markup=markup,
                filename=filename,
                parse_mode=PARSE_MODE,
            )
        except TypeError:
            try:
                result = telegram.send_document(
                    chat_id,
                    path,
                    caption=caption,
                    reply_markup=markup,
                    filename=filename,
                )
            except TypeError:
                result = telegram.send_document(chat_id, path, caption=caption)
    else:
        telegram.send_message(chat_id, caption, reply_markup=markup, parse_mode=PARSE_MODE)
        return
    message_id = ""
    if isinstance(result, dict):
        message_id = str(result.get("provider_message_id") or "")
    remember_sheet_message(str(chat_id), product["id"], message_id)


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
    host = current_host(chat_id)
    send_host_photo(
        telegram,
        chat_id,
        "cheer",
        flavor_caption(
            host,
            "cheer",
            CUSTOMER_CONFIRM.format(detail=detail) + f"\n\n{host['icon']} {pose_line(host, 'soon')}",
        ),
        after_pick_keyboard(product["id"], host),
        host=host,
        effect=True,
    )
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


def _present_host(telegram, chat_id: str, host: dict[str, Any], *, effect: bool = True) -> None:
    caption = flavor_caption(host, "wave")
    if tour_complete(chat_id) and not favorite_id(chat_id):
        caption = (
            f"{caption}\n\n"
            "<b>You have met the whole floor team.</b>\n"
            "Rotate again, or pick a favorite who always serves you."
        )
    send_host_photo(
        telegram,
        chat_id,
        "wave",
        caption,
        quick_menu_keyboard(str(chat_id), host),
        host=host,
        effect=effect,
    )


def _handle_host_callback(telegram, chat_id: str, parts: list[str]) -> dict[str, Any]:
    sub = parts[2] if len(parts) > 2 else ""
    target = parts[3] if len(parts) > 3 else ""
    if sub == "pick":
        host = current_host(chat_id)
        send_host_photo(
            telegram,
            chat_id,
            "present",
            flavor_caption(
                host,
                "present",
                "<b>Pick a favorite.</b>\nThey will greet you every time you come back.",
            ),
            pick_host_keyboard(host),
            host=host,
        )
        return {"ok": True, "action": "host-pick", "chat_id": chat_id}
    if sub == "next":
        host = skip_to_next(chat_id)
        _present_host(telegram, chat_id, host)
        return {"ok": True, "action": "host-next", "chat_id": chat_id, "host": host["id"]}
    if sub == "fav":
        host = set_favorite(chat_id, current_host(chat_id)["id"])
        _present_host(telegram, chat_id, host)
        return {"ok": True, "action": "host-fav", "chat_id": chat_id, "host": host["id"]}
    if sub == "set" and target:
        host = set_favorite(chat_id, target)
        _present_host(telegram, chat_id, host)
        return {"ok": True, "action": "host-set", "chat_id": chat_id, "host": host["id"]}
    if sub == "rotate":
        host = rotate_again(chat_id)
        _present_host(telegram, chat_id, host)
        return {"ok": True, "action": "host-rotate", "chat_id": chat_id, "host": host["id"]}
    return {"ok": True, "ignored": True, "action": "callback-unknown"}


def handle_menu_callback(query: dict[str, Any], telegram) -> dict[str, Any]:
    callback_id = str(query.get("id") or "")
    data = str(query.get("data") or "")
    message = query.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    parts = data.split(":")
    action = parts[1] if len(parts) >= 2 else ""
    host_action = parts[2] if action == "host" and len(parts) > 2 else ""
    if hasattr(telegram, "answer_callback_query") and callback_id:
        telegram.answer_callback_query(callback_id, text=TOASTS.get(host_action or action))
    if not chat_id:
        return {"ok": True, "ignored": True, "action": "callback-no-chat"}
    if len(parts) < 2 or parts[0] != "w":
        return {"ok": True, "ignored": True, "action": "callback-unknown"}
    sku = parts[2] if len(parts) > 2 else ""
    qty = parts[3] if len(parts) > 3 else ""
    if action == "host":
        return _handle_host_callback(telegram, chat_id, parts)
    if action == "menu":
        send_quick_menu(telegram, chat_id)
        return {"ok": True, "action": "menu", "chat_id": chat_id}
    if action == "crew":
        send_crew_photo(telegram, chat_id)
        return {"ok": True, "action": "crew", "chat_id": chat_id}
    if action == "team":
        send_team_card(telegram, chat_id)
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

        host = current_host(chat_id)
        send_host_photo(
            telegram,
            chat_id,
            "work",
            flavor_caption(
                host,
                "work",
                f"<b>How many?</b>\n"
                f"{escape(str(product['name']))} · dry vials\n"
                "\n"
                "Las Vegas · we call to complete docs",
            ),
            qty_keyboard(product["id"], host),
            host=host,
        )
        return {"ok": True, "action": "qty", "chat_id": chat_id, "product": product["id"]}
    if action == "ask" and qty in {"1", "2", "3"}:
        from html import escape

        host = current_host(chat_id)
        send_host_photo(
            telegram,
            chat_id,
            "present",
            flavor_caption(
                host,
                "present",
                f"<b>Confirm</b>\n"
                f"{escape(qty)}× {escape(str(product['name']))}\n"
                f"{escape(str(product['vial']))}\n"
                "\n"
                "Las Vegas residents only\n"
                f"{CALL_AND_DOCS}.",
            ),
            confirm_keyboard(product["id"], qty, host),
            host=host,
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
