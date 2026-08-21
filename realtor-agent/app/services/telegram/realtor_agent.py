"""Realtor Telegram command center: alerts and approve/reject/snooze/details."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import (
    ActorOrigin,
    ActorType,
    OpportunityStatus,
    RejectionReason,
)
from app.models.investor import Investor
from app.models.listing import Listing
from app.models.opportunity import Opportunity
from app.models.realtor import Realtor
from app.services.audit import AuditService
from app.services.communications import CommunicationService
from app.utilities.money import money_label


class RealtorTelegramService:
    def __init__(
        self,
        db: Session,
        comms: CommunicationService | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self.db = db
        self.audit = audit or AuditService(db)
        self.comms = comms or CommunicationService(db, audit=self.audit)

    def alert_opportunity(self, realtor: Realtor, opportunity: Opportunity) -> None:
        listing = self.db.get(Listing, opportunity.listing_id)
        investor = self.db.get(Investor, opportunity.investor_id)
        if listing is None or investor is None:
            return
        chat_id = realtor.telegram_chat_id or realtor.telegram_user_id or "mock-realtor"
        settings = get_settings()
        if settings.telegram_mode == "live" and chat_id in {None, "", "mock-realtor"}:
            raise ValueError(
                "Telegram chat is not linked. Open the bot on your phone and send /start, "
                "or set TELEGRAM_OPERATOR_CHAT_ID."
            )
        explanation = opportunity.explanation or {}
        context = {
            "address": listing.street_address,
            "city": listing.city,
            "state": listing.state,
            "price": money_label(listing.asking_price),
            "beds": listing.bedrooms,
            "baths": listing.bathrooms,
            "sqft": f"{listing.sqft:,}" if listing.sqft else "n/a",
            "investor": investor.name,
            "score": f"{float(opportunity.score):.0f}%",
            "reasons": explanation.get("reasons") or [],
            "issues": explanation.get("potential_issues") or [],
            "listing_url": listing.listing_url or "",
            "opportunity_id": opportunity.public_id,
            "needs_arv": bool(explanation.get("needs_arv")),
            "screening": explanation.get("screening") or {},
        }
        oid = opportunity.public_id
        buttons: list[list[dict[str, str]]] = []
        if listing.listing_url:
            buttons.append([{"text": "VIEW LISTING", "url": listing.listing_url}])
        buttons.append(
            [
                {"text": "APPROVE", "callback_data": f"approve:{oid}"},
                {"text": "REJECT", "callback_data": f"reject:{oid}"},
            ]
        )
        buttons.append(
            [
                {"text": "SNOOZE", "callback_data": f"snooze:{oid}"},
                {"text": "DETAILS", "callback_data": f"details:{oid}"},
            ]
        )
        self.comms.send_message(
            realtor=realtor,
            recipient=chat_id,
            channel="telegram",
            template="opportunity_alert.txt.j2",
            context=context,
            opportunity_id=opportunity.id,
            investor_id=investor.id,
            buttons=buttons,
        )
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type="TELEGRAM_ALERT_SENT",
            message="Telegram alert sent to realtor",
            opportunity_id=opportunity.id,
            listing_id=listing.id,
            investor_id=investor.id,
        )

    def approve(self, realtor: Realtor, opportunity: Opportunity, notes: str | None = None) -> Opportunity:
        if opportunity.status == OpportunityStatus.AWAITING_ARV.value:
            raise ValueError("Enter ARV and re-screen before approving this opportunity")
        before = opportunity.status
        opportunity.status = OpportunityStatus.APPROVED_FOR_INVESTOR_NOTIFICATION.value
        opportunity.reviewed_at = datetime.now(timezone.utc)
        self._log_decision(realtor, opportunity, "APPROVE_INVESTOR_NOTIFICATION", before, notes)
        return opportunity

    def reject(
        self,
        realtor: Realtor,
        opportunity: Opportunity,
        reason: RejectionReason,
        notes: str | None = None,
    ) -> Opportunity:
        before = opportunity.status
        opportunity.status = OpportunityStatus.REJECTED.value
        opportunity.rejection_reason = reason.value
        opportunity.rejection_notes = notes
        opportunity.reviewed_at = datetime.now(timezone.utc)
        self._log_decision(realtor, opportunity, "REJECT_OPPORTUNITY", before, notes, extra={"reason": reason.value})
        return opportunity

    def snooze(self, realtor: Realtor, opportunity: Opportunity, hours: int = 24, notes: str | None = None) -> Opportunity:
        before = opportunity.status
        opportunity.status = OpportunityStatus.SNOOZED.value
        opportunity.snooze_until = datetime.now(timezone.utc) + timedelta(hours=hours)
        opportunity.reviewed_at = datetime.now(timezone.utc)
        self._log_decision(realtor, opportunity, "SNOOZE_OPPORTUNITY", before, notes)
        return opportunity

    def details(self, opportunity: Opportunity) -> dict:
        listing = self.db.get(Listing, opportunity.listing_id)
        investor = self.db.get(Investor, opportunity.investor_id)
        return {
            "opportunity_id": opportunity.public_id,
            "status": opportunity.status,
            "score": float(opportunity.score),
            "explanation": opportunity.explanation,
            "listing": {
                "mls_id": listing.mls_listing_id if listing else None,
                "address": listing.street_address if listing else None,
                "url": listing.listing_url if listing else None,
                "remarks": listing.remarks if listing else None,
            },
            "investor": investor.name if investor else None,
            "review_notice": "Realtor approval is required before any investor is notified.",
        }

    def handle_callback(self, realtor: Realtor, callback_data: str) -> dict:
        action, _, public_id = callback_data.partition(":")
        opportunity = (
            self.db.query(Opportunity)
            .filter(Opportunity.public_id == public_id, Opportunity.realtor_id == realtor.id)
            .one_or_none()
        )
        if opportunity is None:
            return {"ok": False, "error": "opportunity not found"}
        if action == "approve":
            self.approve(realtor, opportunity)
            return {"ok": True, "action": "approve", "opportunity_id": public_id, "status": opportunity.status}
        if action == "reject":
            self.reject(realtor, opportunity, RejectionReason.OTHER, "Rejected from Telegram")
            return {"ok": True, "action": "reject", "opportunity_id": public_id, "status": opportunity.status}
        if action == "snooze":
            self.snooze(realtor, opportunity)
            return {"ok": True, "action": "snooze", "opportunity_id": public_id, "status": opportunity.status}
        if action == "details":
            return {"ok": True, "action": "details", "details": self.details(opportunity)}
        if action == "view":
            listing = self.db.get(Listing, opportunity.listing_id)
            return {"ok": True, "action": "view", "url": listing.listing_url if listing else None}
        return {"ok": False, "error": f"unknown action {action}"}

    def _log_decision(
        self,
        realtor: Realtor,
        opportunity: Opportunity,
        event: str,
        before: str,
        notes: str | None,
        extra: dict | None = None,
    ) -> None:
        self.audit.record(
            event=event,
            object_type="opportunity",
            object_id=opportunity.public_id,
            actor=realtor.public_id,
            actor_type=ActorType.REALTOR.value,
            origin=ActorOrigin.HUMAN.value,
            realtor_id=str(realtor.id),
            before_state={"status": before},
            after_state={"status": opportunity.status, **(extra or {})},
            detail=notes,
        )
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type=event,
            message=f"Realtor {event.replace('_', ' ').lower()}",
            opportunity_id=opportunity.id,
            listing_id=opportunity.listing_id,
            investor_id=opportunity.investor_id,
            actor_type=ActorType.REALTOR.value,
            actor_id=realtor.public_id,
        )
        self.audit.analytics(realtor.id, event.lower(), {"opportunity_id": opportunity.public_id})
