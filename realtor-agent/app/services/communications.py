"""Unified communication service.

send_message(recipient, channel, template, context)
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.integrations.email.base import EmailProvider
from app.integrations.telegram.base import TelegramProvider
from app.integrations.twilio.base import SMSProvider
from app.models.communication import Communication
from app.models.enums import (
    ActorOrigin,
    ActorType,
    CommunicationDirection,
    DeliveryStatus,
    NotificationChannel,
)
from app.models.investor import Investor
from app.models.realtor import Realtor
from app.services.audit import AuditService
from app.services.notifications.templates import render_template
from app.services.providers import get_email_provider, get_sms_provider, get_telegram_provider
from app.utilities.ids import next_public_id


class CommunicationService:
    def __init__(
        self,
        db: Session,
        telegram: TelegramProvider | None = None,
        sms: SMSProvider | None = None,
        email: EmailProvider | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self.db = db
        self.telegram = telegram or get_telegram_provider()
        self.sms = sms or get_sms_provider()
        self.email = email or get_email_provider()
        self.audit = audit or AuditService(db)

    def send_message(
        self,
        *,
        realtor: Realtor,
        recipient: str,
        channel: str,
        template: str,
        context: dict,
        opportunity_id=None,
        transaction_id=None,
        investor_id=None,
        buttons: list[dict[str, str]] | None = None,
    ) -> Communication:
        body = render_template(channel, template, context)
        row = Communication(
            public_id=next_public_id(self.db, "COM"),
            realtor_id=realtor.id,
            opportunity_id=opportunity_id,
            transaction_id=transaction_id,
            investor_id=investor_id,
            channel=channel,
            template=template,
            direction=CommunicationDirection.OUTBOUND.value,
            recipient=recipient,
            body=body,
            status=DeliveryStatus.QUEUED.value,
            provider=channel,
        )
        self.db.add(row)
        self.db.flush()
        try:
            result = self._dispatch(channel, recipient, body, buttons)
            row.provider = result.get("provider") or channel
            row.provider_message_id = result.get("provider_message_id")
            row.status = result.get("status") or DeliveryStatus.SENT.value
            row.sent_at = datetime.now(timezone.utc)
            if row.status in {DeliveryStatus.DELIVERED.value, "delivered"}:
                row.delivered_at = row.sent_at
                row.status = DeliveryStatus.DELIVERED.value
        except Exception as exc:  # noqa: BLE001
            row.status = DeliveryStatus.FAILED.value
            row.error_detail = str(exc)
            self.audit.record(
                event="COMMUNICATION_FAILED",
                object_type="communication",
                object_id=row.public_id,
                actor="communication_service",
                realtor_id=str(realtor.id),
                detail=str(exc),
            )
            raise
        self.audit.record(
            event="MESSAGE_SENT",
            object_type="communication",
            object_id=row.public_id,
            actor="communication_service",
            actor_type=ActorType.SYSTEM.value,
            origin=ActorOrigin.AUTOMATION.value,
            realtor_id=str(realtor.id),
            after_state={"channel": channel, "recipient": recipient},
        )
        if investor_id:
            investor = self.db.get(Investor, investor_id)
            if investor:
                investor.last_contact_at = datetime.now(timezone.utc)
        return row

    def _dispatch(self, channel: str, recipient: str, body: str, buttons: list[dict[str, str]] | None) -> dict:
        if channel == NotificationChannel.TELEGRAM.value:
            result = self.telegram.send_message(recipient, body, buttons)
            result.setdefault("provider", self.telegram.name)
            result.setdefault("status", DeliveryStatus.SENT.value)
            return result
        if channel == NotificationChannel.SMS.value:
            result = self.sms.send_sms(recipient, body)
            result.setdefault("provider", self.sms.name)
            return result
        if channel == NotificationChannel.EMAIL.value:
            result = self.email.send_email(recipient, "Property opportunity", body)
            result.setdefault("provider", self.email.name)
            return result
        raise ValueError(f"Channel {channel} is not enabled in this MVP")
