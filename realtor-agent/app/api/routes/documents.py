from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.dependencies import ActiveRealtor, DbSession
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.transaction import Transaction
from app.schemas.document import DocumentGenerateRequest, DocumentRead, DocumentValidation
from app.services.documents.engine import DocumentEngine, DocumentValidationError
from app.services.transactions.engine import InvalidTransition

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(db: DbSession, realtor: ActiveRealtor) -> list[Document]:
    return db.query(Document).filter(Document.realtor_id == realtor.id).all()


@router.post("/validate/{transaction_id}", response_model=DocumentValidation)
def validate_document(transaction_id: UUID, db: DbSession, realtor: ActiveRealtor) -> dict:
    transaction = _transaction(db, realtor, transaction_id)
    return DocumentEngine(db).validate(transaction)


@router.post("/generate/{transaction_id}", response_model=DocumentRead)
def generate_document(
    transaction_id: UUID,
    payload: DocumentGenerateRequest,
    db: DbSession,
    realtor: ActiveRealtor,
) -> Document:
    transaction = _transaction(db, realtor, transaction_id)
    try:
        document = DocumentEngine(db).generate(
            realtor, transaction, payload.template_name, payload.template_version
        )
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Cannot generate purchase agreement.",
                "missing": exc.missing,
                "review_notice": "Draft documents require realtor review. Missing contractual values are never invented.",
            },
        ) from exc
    db.commit()
    db.refresh(document)
    return document


@router.post("/{document_id}/ready", response_model=DocumentRead)
def mark_ready(document_id: UUID, db: DbSession, realtor: ActiveRealtor) -> Document:
    return _move(db, realtor, document_id, DocumentStatus.READY_FOR_REVIEW)


@router.post("/{document_id}/approve", response_model=DocumentRead)
def approve_document(document_id: UUID, db: DbSession, realtor: ActiveRealtor) -> Document:
    return _move(db, realtor, document_id, DocumentStatus.APPROVED_BY_REALTOR)


def _move(db, realtor, document_id: UUID, status: DocumentStatus) -> Document:
    document = (
        db.query(Document).filter(Document.id == document_id, Document.realtor_id == realtor.id).one_or_none()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        DocumentEngine(db).transition(realtor, document, status)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(document)
    return document


def _transaction(db, realtor, transaction_id: UUID) -> Transaction:
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.realtor_id == realtor.id)
        .one_or_none()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction
