"""Inbound Telegram for TrueHold Wellness: inbox, inventory sheets, and orders."""

from __future__ import annotations

from wellness_agent.catalog import (
    UnknownProductError,
    find_product,
    format_catalog,
    format_product_caption,
    pdf_path,
)
from wellness_agent.compose import compose_alert, format_alert
from wellness_agent.identity import REQUIRED_USERNAME
from wellness_agent.models import AlertTrigger
from wellness_agent.operator_store import remember_operator
from wellness_agent.reflex import fire_reflex

HELP = (
    f"TrueHold Wellness (@{REQUIRED_USERNAME})\n"
    "/start — link this chat\n"
    "/inbox — full business inbox snapshot (orders, payments, fulfillment, shipping, cancellations, peptides)\n"
    "/catalog — live shop inventory and locked information sheets\n"
    "/product <name> — send a locked PDF (tirzepatide, retatrutide, semax, nad, klow, mots-c, ss-31, ghk-cu)\n"
    "/order <detail> — record an interest order and notify operators\n"
    "/schedule — book with the TrueHold team\n"
    "/help — this message\n"
    "Educational only. Protocol details reviewed case by case.\n"
    "This bot is not realtor-agent / @PirateEye_bot."
)

SCHEDULE = (
    "TrueHold Wellness — book with the team\n"
    "Phone: (702) 879-8783 or (702) 879-TRUE\n"
    "Email: TRUEHOLDWELLNESS@GMAIL.COM\n"
    "Shop: https://trueholdwellness.com/shop\n"
    "Las Vegas residents only for Telegram interest orders.\n"
    "Protocol details are reviewed case by case. "
    "This bot does not provide dosing, reconstitution, or administration instructions in chat."
)

BOT_COMMANDS = (
    {"command": "start", "description": "Link this chat as the Wellness operator"},
    {"command": "inbox", "description": "Full business inbox snapshot"},
    {"command": "catalog", "description": "Live shop inventory"},
    {"command": "product", "description": "Send a locked information sheet PDF"},
    {"command": "order", "description": "Interest order; notifies operators with inbox snapshot"},
    {"command": "schedule", "description": "Book with the TrueHold team"},
    {"command": "help", "description": "Command list"},
)


def _product_query(text: str, command: str) -> str:
    rest = text[len(command) :].strip()
    if rest.startswith("@"):
        parts = rest.split(None, 1)
        rest = parts[1] if len(parts) > 1 else ""
    return rest


def _matched_product(detail: str):
    tokens = [part for part in detail.replace("/", " ").replace(",", " ").split() if len(part) >= 3]
    for token in (detail, *tokens):
        try:
            return find_product(token)
        except UnknownProductError:
            continue
    return None


def handle_telegram_update(payload: dict, telegram) -> dict:
    message = payload.get("message") or {}
    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    if not chat_id:
        return {"ok": True, "ignored": True}
    lowered = text.lower()
    if lowered.startswith("/start") or lowered in {"/help", "help"}:
        if lowered.startswith("/start"):
            remember_operator(chat_id)
            telegram.send_message(
                chat_id,
                f"Linked as TrueHold Wellness operator on @{REQUIRED_USERNAME}.\n"
                "You will get order and email-reflex alerts here "
                "(orders, payments, fulfillment, shipping, cancellations, peptides).\n"
                "This bot is not realtor-agent / @PirateEye_bot.",
            )
        telegram.send_message(chat_id, HELP)
        return {"ok": True, "action": "help", "chat_id": chat_id}
    if lowered.startswith("/inbox"):
        alert = compose_alert(AlertTrigger(type="business", headline="business inbox"))
        telegram.send_message(chat_id, format_alert(alert))
        return {"ok": True, "action": "inbox", "chat_id": chat_id}
    if lowered.startswith("/catalog"):
        telegram.send_message(chat_id, format_catalog())
        return {"ok": True, "action": "catalog", "chat_id": chat_id}
    if lowered.startswith("/schedule"):
        telegram.send_message(chat_id, SCHEDULE)
        return {"ok": True, "action": "schedule", "chat_id": chat_id}
    if lowered.startswith("/product") or lowered.startswith("/sheet"):
        command = "/product" if lowered.startswith("/product") else "/sheet"
        query = _product_query(text, command)
        if not query:
            telegram.send_message(chat_id, "Send /product <name>. Use /catalog for the live list.")
            return {"ok": True, "action": "product-help", "chat_id": chat_id}
        try:
            product = find_product(query)
            path = pdf_path(product)
        except (UnknownProductError, FileNotFoundError) as exc:
            telegram.send_message(chat_id, str(exc))
            return {"ok": False, "action": "product-miss", "chat_id": chat_id, "error": str(exc)}
        telegram.send_document(chat_id, path, caption=format_product_caption(product))
        return {"ok": True, "action": "product", "chat_id": chat_id, "product": product["id"]}
    if lowered.startswith("/order") or lowered.startswith("order:"):
        detail = text.split(None, 1)[1] if " " in text else text
        if detail.lower() in {"/order", "order:"}:
            telegram.send_message(chat_id, "Send /order <product and qty> to take an interest order.")
            return {"ok": True, "action": "order-help", "chat_id": chat_id}
        result = fire_reflex(
            "order",
            detail,
            exclude_chats={chat_id},
            require_destination=False,
        )
        telegram.send_message(chat_id, result.text)
        telegram.send_message(
            chat_id,
            "Interest order recorded on TrueHold Wellness. Operators are notified "
            "with the full inbox snapshot (orders, payments, fulfillment, shipping, "
            f"cancellations, peptides).\n{detail}",
        )
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
    return {"ok": True, "ignored": True}
