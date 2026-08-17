"""Notify investors only after explicit realtor approval."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.enums import (
    ActorOrigin,
    ActorType,
    InvestorResponse,
    OpportunityStatus,
    TransactionStatus,
)
from app.models.investor import Investor
from app.models.listing import Listing
from app.models.opportunity import Opportunity
from app.models.realtor import Realtor
from app.services.audit import AuditService
from app.services.communications import CommunicationService
from app.services.transactions.engine import TransactionService
from app.utilities.money import money_label


class InvestorNotificationService:
    def __init__(
        self,
        db: Session,
        comms: CommunicationService | None = None,
        audit: AuditService | None = None,
        transactions: TransactionService | None = None,
    ) -> None:
        self.db = db
        self.audit = audit or AuditService(db)
        self.comms = comms or CommunicationService(db, audit=self.audit)
        self.transactions = transactions or TransactionService(db, audit=self.audit)

    def notify_approved(self, realtor: Realtor, opportunity: Opportunity) -> None:
        if opportunity.status != OpportunityStatus.APPROVED_FOR_INVESTOR_NOTIFICATION.value:
            raise ValueError("Opportunity is not approved for investor notification")
        investor = self.db.get(Investor, opportunity.investor_id)
        listing = self.db.get(Listing, opportunity.listing_id)
        if investor is None or listing is None:
            raise ValueError("Investor or listing missing")
        permissions = investor.communication_permissions or {}
        channel = investor.preferred_channel or "sms"
        if channel == "sms" and permissions.get("sms") is False:
            raise ValueError("Investor has not permitted SMS")
        recipient = investor.phone if channel == "sms" else (investor.email or investor.phone or "unknown")
        context = {
            "address": listing.street_address,
            "city": listing.city,
            "state": listing.state,
            "zip_code": listing.zip_code,
            "price": money_label(listing.asking_price),
            "beds": listing.bedrooms,
            "baths": listing.bathrooms,
            "sqft": f"{listing.sqft:,}" if listing.sqft else "n/a",
            "profile_name": "current acquisition",
        }
        template = "opportunity.txt.j2" if channel == "sms" else "opportunity.txt.j2"
        folder = "sms" if channel == "sms" else "email"
        self.comms.send_message(
            realtor=realtor,
            recipient=recipient or "unknown",
            channel=folder,
            template=template,
            context=context,
            opportunity_id=opportunity.id,
            investor_id=investor.id,
        )
        opportunity.status = OpportunityStatus.INVESTOR_NOTIFIED.value
        opportunity.notified_investor_at = datetime.now(timezone.utc)
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type="INVESTOR_NOTIFIED",
            message=f"{channel.upper()} delivered to investor",
            opportunity_id=opportunity.id,
            listing_id=listing.id,
            investor_id=investor.id,
        )

    def record_response(
        self,
        realtor: Realtor,
        opportunity: Opportunity,
        response: InvestorResponse,
        body: str | None = None,
    ):
        opportunity  # noqa: B018
        if response == InvestorResponse.YES:
            opportunity.status = OpportunityStatus.INVESTOR_INTERESTED.value
            transaction = self.transactions.create_from_opportunity(realtor, opportunity)
            self.audit.timeline(
                realtor_id=realtor.id,
                event_type="INVESTOR_RESPONDED_YES",
                message="Investor responded YES",
                opportunity_id=opportunity.id,
                transaction_id=transaction.id,
                investor_id=opportunity.investor_id,
                actor_type=ActorType.INVESTOR.value,
            )
            return transaction
        if response == InvestorResponse.NO:
            opportunity.status = OpportunityStatus.INVESTOR_DECLINED.value
            self.audit.timeline(
                realtor_id=realtor.id,
                event_type="INVESTOR_RESPONDED_NO",
                message="Investor responded NO",
                opportunity_id=opportunity.id,
                investor_id=opportunity.investor_id,
                actor_type=ActorType.INVESTOR.value,
            )
            return None
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type="INVESTOR_REQUESTED_INFO",
            message=body or "Investor requested more information",
            opportunity_id=opportunity.id,
            investor_id=opportunity.investor_id,
            actor_type=ActorType.INVESTOR.value,
        )
        return None
