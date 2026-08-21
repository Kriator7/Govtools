"""Transaction state machine. Status is never inferred from free-text messages."""

from sqlalchemy.orm import Session

from app.models.enums import (
    TRANSACTION_TRANSITIONS,
    ActorOrigin,
    ActorType,
    TransactionStatus,
)
from app.models.opportunity import Opportunity
from app.models.realtor import Realtor
from app.models.transaction import Transaction
from app.services.audit import AuditService
from app.utilities.ids import next_public_id


class InvalidTransition(ValueError):
    pass


class TransactionService:
    def __init__(self, db: Session, audit: AuditService | None = None) -> None:
        self.db = db
        self.audit = audit or AuditService(db)

    def create_from_opportunity(self, realtor: Realtor, opportunity: Opportunity) -> Transaction:
        existing = (
            self.db.query(Transaction)
            .filter(Transaction.opportunity_id == opportunity.id)
            .one_or_none()
        )
        if existing:
            return existing
        transaction = Transaction(
            public_id=next_public_id(self.db, "TX"),
            realtor_id=realtor.id,
            opportunity_id=opportunity.id,
            listing_id=opportunity.listing_id,
            investor_id=opportunity.investor_id,
            criteria_id=opportunity.criteria_id,
            status=TransactionStatus.INVESTOR_INTERESTED.value,
            buyer_legal_name=None,
        )
        self.db.add(transaction)
        self.db.flush()
        opportunity.transaction_id = transaction.id
        self.audit.record(
            event="TRANSACTION_CREATED",
            object_type="transaction",
            object_id=transaction.public_id,
            actor="transaction_engine",
            actor_type=ActorType.SYSTEM.value,
            origin=ActorOrigin.AUTOMATION.value,
            realtor_id=str(realtor.id),
            after_state={"status": transaction.status, "opportunity": opportunity.public_id},
        )
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type="TRANSACTION_CREATED",
            message=f"Transaction {transaction.public_id} created",
            opportunity_id=opportunity.id,
            transaction_id=transaction.id,
            listing_id=opportunity.listing_id,
            investor_id=opportunity.investor_id,
        )
        return transaction

    def transition(
        self,
        realtor: Realtor,
        transaction: Transaction,
        new_status: TransactionStatus,
        notes: str | None = None,
        actor: str = "system",
        origin: str = ActorOrigin.AUTOMATION.value,
    ) -> Transaction:
        current = TransactionStatus(transaction.status)
        allowed = TRANSACTION_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise InvalidTransition(f"Cannot transition {current.value} -> {new_status.value}")
        before = transaction.status
        transaction.status = new_status.value
        if notes:
            transaction.notes = ((transaction.notes or "") + f"\n{notes}").strip()
        self.audit.record(
            event="TRANSACTION_STATUS_CHANGED",
            object_type="transaction",
            object_id=transaction.public_id,
            actor=actor,
            origin=origin,
            realtor_id=str(realtor.id),
            before_state={"status": before},
            after_state={"status": transaction.status},
            detail=notes,
        )
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type="TRANSACTION_STATUS_CHANGED",
            message=f"Transaction moved {before} -> {transaction.status}",
            transaction_id=transaction.id,
            opportunity_id=transaction.opportunity_id,
        )
        return transaction
