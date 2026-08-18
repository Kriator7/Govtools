"""Persist and notify TrueHold Wellness orders. Does not touch realtor-agent."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from thw.email_inbox import load_inbox, parse_order_email
from thw.identity import REQUIRED_USERNAME
from thw.models import Operator, WellnessOrder
from thw.providers import get_telegram


def next_order_id(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(WellnessOrder).count() + 1
    return f"THW-{year}-{count:06d}"


def get_or_create_operator(db: Session, chat_id: str | None = None) -> Operator:
    operator = db.query(Operator).order_by(Operator.id.asc()).first()
    if operator is None:
        operator = Operator(telegram_chat_id=chat_id, notes="TrueHold Wellness operator")
        db.add(operator)
        db.flush()
        return operator
    if chat_id:
        operator.telegram_chat_id = chat_id
    return operator


def ingest_inbox(db: Session, inbox_path) -> list[WellnessOrder]:
    created: list[WellnessOrder] = []
    for raw in load_inbox(inbox_path):
        parsed = parse_order_email(raw)
        source_id = parsed.get("source_message_id") or ""
        if source_id:
            existing = db.query(WellnessOrder).filter(WellnessOrder.source_message_id == source_id).one_or_none()
            if existing:
                continue
        order = WellnessOrder(
            public_id=next_order_id(db),
            from_address=parsed["from_address"],
            subject=parsed["subject"],
            body=parsed["body"],
            customer_name=parsed.get("customer_name"),
            product=parsed.get("product"),
            quantity=parsed.get("quantity"),
            source_message_id=source_id or None,
            status="RECEIVED",
        )
        db.add(order)
        db.flush()
        created.append(order)
    return created


def notify_order(db: Session, order: WellnessOrder, telegram=None) -> None:
    telegram = telegram or get_telegram()
    operator = get_or_create_operator(db)
    chat_id = operator.telegram_chat_id or "mock-wellness-operator"
    text = (
        "TrueHold Wellness order\n"
        f"{order.public_id}\n"
        f"From: {order.from_address}\n"
        f"Subject: {order.subject}\n"
        f"Customer: {order.customer_name or 'n/a'}\n"
        f"Product: {order.product or 'n/a'}\n"
        f"Qty: {order.quantity or 'n/a'}\n"
        f"This alert is @{REQUIRED_USERNAME} only — not PirateEye / realtor-agent."
    )
    telegram.send_message(chat_id, text)
    order.telegram_notified_at = datetime.now(timezone.utc)
    order.status = "NOTIFIED"
    try:
        from wellness_agent.reflex import fire_reflex

        fire_reflex(
            "order",
            text,
            exclude_chats={str(chat_id)},
            require_destination=False,
        )
    except Exception:
        # Telegram order card already sent. Webhook/operator snapshot is best-effort.
        pass


def handle_telegram_update(db: Session, payload: dict, telegram=None) -> dict:
    telegram = telegram or get_telegram()
    message = payload.get("message") or {}
    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    if text.startswith("/start") and chat_id:
        get_or_create_operator(db, chat_id)
        telegram.send_message(
            chat_id,
            f"Linked as TrueHold Wellness operator on @{REQUIRED_USERNAME}.\n"
            "You will get order-email alerts here.\n"
            "This bot is not realtor-agent / @PirateEye_bot.",
        )
        return {"ok": True, "action": "linked", "chat_id": chat_id}
    return {"ok": True, "ignored": True}
