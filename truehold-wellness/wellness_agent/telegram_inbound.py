"""Inbound Telegram for TrueHold Wellness: take orders and deliver inbox messages."""

from __future__ import annotations

from wellness_agent.compose import compose_alert, format_alert
from wellness_agent.identity import REQUIRED_USERNAME
from wellness_agent.models import AlertTrigger

HELP = (
    f"TrueHold Wellness (@{REQUIRED_USERNAME})\n"
    "/start — link this chat\n"
    "/inbox — full business inbox snapshot (orders, payments, fulfillment, shipping, cancellations, peptides)\n"
    "/order <detail> — record an order and send confirmation\n"
    "/help — this message\n"
    "This bot is not realtor-agent / @PirateEye_bot."
)

BOT_COMMANDS = (
    {"command": "start", "description": "Link this chat as the Wellness operator"},
    {"command": "inbox", "description": "Full business inbox snapshot"},
    {"command": "order", "description": "Record an order: /order <product and qty>"},
    {"command": "help", "description": "Command list"},
)


def handle_telegram_update(payload: dict, telegram) -> dict:
    message = payload.get("message") or {}
    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    if not chat_id:
        return {"ok": True, "ignored": True}
    lowered = text.lower()
    if lowered.startswith("/start") or lowered in {"/help", "help"}:
        telegram.send_message(chat_id, HELP)
        return {"ok": True, "action": "help", "chat_id": chat_id}
    if lowered.startswith("/inbox"):
        alert = compose_alert(AlertTrigger(type="business", headline="business inbox"))
        telegram.send_message(chat_id, format_alert(alert))
        return {"ok": True, "action": "inbox", "chat_id": chat_id}
    if lowered.startswith("/order") or lowered.startswith("order:"):
        detail = text.split(None, 1)[1] if " " in text else text
        if detail.lower() in {"/order", "order:"}:
            telegram.send_message(chat_id, "Send /order <product and qty> to take an order.")
            return {"ok": True, "action": "order-help", "chat_id": chat_id}
        alert = compose_alert(
            AlertTrigger(type="order", headline="order", detail=detail)
        )
        telegram.send_message(chat_id, format_alert(alert))
        telegram.send_message(chat_id, f"Order recorded on TrueHold Wellness.\n{detail}")
        return {"ok": True, "action": "order", "chat_id": chat_id, "detail": detail}
    return {"ok": True, "ignored": True}
