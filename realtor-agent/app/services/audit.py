"""Immutable-style audit and timeline writers."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.analytics_event import AnalyticsEvent
from app.models.audit_log import AuditLog
from app.models.enums import ActorOrigin, ActorType


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        event: str,
        object_type: str,
        object_id: str,
        actor: str,
        actor_type: str = ActorType.SYSTEM.value,
        origin: str = ActorOrigin.AUTOMATION.value,
        realtor_id: str | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
        detail: str | None = None,
        service: str | None = None,
    ) -> AuditLog:
        row = AuditLog(
            realtor_id=realtor_id,
            actor=actor,
            actor_type=actor_type,
            origin=origin,
            event=event,
            object_type=object_type,
            object_id=str(object_id),
            before_state=before_state,
            after_state=after_state,
            detail=detail,
            service=service or "realtor-agent",
        )
        self.db.add(row)
        self.db.flush()
        return row

    def timeline(
        self,
        *,
        realtor_id: UUID,
        event_type: str,
        message: str,
        opportunity_id: UUID | None = None,
        transaction_id: UUID | None = None,
        listing_id: UUID | None = None,
        investor_id: UUID | None = None,
        actor_type: str = ActorType.SYSTEM.value,
        actor_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> ActivityLog:
        row = ActivityLog(
            realtor_id=realtor_id,
            event_type=event_type,
            message=message,
            opportunity_id=opportunity_id,
            transaction_id=transaction_id,
            listing_id=listing_id,
            investor_id=investor_id,
            actor_type=actor_type,
            actor_id=actor_id,
            extra=extra,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def analytics(self, realtor_id: UUID, event_name: str, properties: dict | None = None) -> AnalyticsEvent:
        row = AnalyticsEvent(
            realtor_id=realtor_id,
            event_name=event_name,
            properties=properties or {},
        )
        self.db.add(row)
        self.db.flush()
        return row
