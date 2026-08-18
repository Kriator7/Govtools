"""Notify investors only after explicit realtor approval.

Damian’s live preference is SMS. During testing, SMS is relayed to SMS_RELAY_TO
(if set) and an email copy is sent to the CardanoMint relay inbox.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import (
    ActorType,
    InvestorResponse,
    OpportunityStatus,
)
from app.models.investor import Investor
from app.models.listing import Listing
from app.models.opportunity import Opportunity
from app.models.realtor import Realtor
from app.services.audit import AuditService
from app.services.communications import CommunicationService
from app.services.sms.relay import resolve_sms_destination
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
        settings = get_settings()
        permissions = investor.communication_permissions or {}
        preferred = (investor.preferred_channel or "sms").lower()
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
        sent_channels: list[str] = []

        if preferred == "sms":
            dest = resolve_sms_destination(investor.phone, settings)
            if permissions.get("sms") is not True:
                self._hold(realtor, opportunity, listing, investor, "INVESTOR_SMS_HELD", "SMS held: investor has not confirmed text permission")
            elif not dest.get("to"):
                self._hold(
                    realtor,
                    opportunity,
                    listing,
                    investor,
                    "INVESTOR_SMS_HELD",
                    "SMS held: no relay/test phone. Set SMS_RELAY_TO to your number before live Twilio.",
                )
            else:
                self.comms.send_message(
                    realtor=realtor,
                    recipient=investor.phone or dest["to"],
                    channel="sms",
                    template="opportunity.txt.j2",
                    context=context,
                    opportunity_id=opportunity.id,
                    investor_id=investor.id,
                )
                sent_channels.append("sms")

        send_email = preferred == "email" or settings.notify_email_copy
        if send_email:
            email_allowed = permissions.get("email") is True or (
                settings.notify_email_copy and preferred == "sms"
            )
            if not email_allowed:
                self._hold(
                    realtor,
                    opportunity,
                    listing,
                    investor,
                    "INVESTOR_EMAIL_HELD",
                    "Email held: investor has not confirmed email permission",
                )
            else:
                self.comms.send_message(
                    realtor=realtor,
                    recipient=investor.email or settings.email_relay_to,
                    channel="email",
                    template="opportunity.txt.j2",
                    context=context,
                    opportunity_id=opportunity.id,
                    investor_id=investor.id,
                )
                sent_channels.append("email")

        if not sent_channels:
            return
        opportunity.status = OpportunityStatus.INVESTOR_NOTIFIED.value
        opportunity.notified_investor_at = datetime.now(timezone.utc)
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type="INVESTOR_NOTIFIED",
            message=f"{'+'.join(item.upper() for item in sent_channels)} delivered to investor channel (test relays may apply)",
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

    def _hold(
        self,
        realtor: Realtor,
        opportunity: Opportunity,
        listing: Listing,
        investor: Investor,
        event_type: str,
        message: str,
    ) -> None:
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type=event_type,
            message=message,
            opportunity_id=opportunity.id,
            listing_id=listing.id,
            investor_id=investor.id,
        )
