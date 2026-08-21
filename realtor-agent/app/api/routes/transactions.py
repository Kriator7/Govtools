from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.dependencies import ActiveRealtor, DbSession
from app.models.activity_log import ActivityLog
from app.models.opportunity import Opportunity
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionTransition,
    TransactionUpdate,
)
from app.services.transactions.engine import InvalidTransition, TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionRead])
def list_transactions(db: DbSession, realtor: ActiveRealtor) -> list[Transaction]:
    return db.query(Transaction).filter(Transaction.realtor_id == realtor.id).all()


@router.post("", response_model=TransactionRead, status_code=201)
def create_transaction(payload: TransactionCreate, db: DbSession, realtor: ActiveRealtor) -> Transaction:
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.id == payload.opportunity_id, Opportunity.realtor_id == realtor.id)
        .one_or_none()
    )
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    service = TransactionService(db)
    transaction = service.create_from_opportunity(realtor, opportunity)
    for key, value in payload.model_dump(exclude={"opportunity_id"}, exclude_unset=True).items():
        setattr(transaction, key, value)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: UUID, db: DbSession, realtor: ActiveRealtor) -> Transaction:
    return _get(db, realtor, transaction_id)


@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: UUID, payload: TransactionUpdate, db: DbSession, realtor: ActiveRealtor
) -> Transaction:
    transaction = _get(db, realtor, transaction_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(transaction, key, value)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/{transaction_id}/transition", response_model=TransactionRead)
def transition_transaction(
    transaction_id: UUID, payload: TransactionTransition, db: DbSession, realtor: ActiveRealtor
) -> Transaction:
    transaction = _get(db, realtor, transaction_id)
    try:
        TransactionService(db).transition(realtor, transaction, payload.status, payload.notes, actor=realtor.public_id)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/{transaction_id}/timeline")
def transaction_timeline(transaction_id: UUID, db: DbSession, realtor: ActiveRealtor) -> list[dict]:
    transaction = _get(db, realtor, transaction_id)
    rows = (
        db.query(ActivityLog)
        .filter(ActivityLog.transaction_id == transaction.id)
        .order_by(ActivityLog.occurred_at.asc())
        .all()
    )
    return [
        {
            "occurred_at": row.occurred_at.isoformat(),
            "event_type": row.event_type,
            "message": row.message,
            "actor_type": row.actor_type,
        }
        for row in rows
    ]


def _get(db, realtor, transaction_id: UUID) -> Transaction:
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.realtor_id == realtor.id)
        .one_or_none()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction
