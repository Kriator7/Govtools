from fastapi import APIRouter

from app.dependencies import ActiveRealtor, DbSession
from app.models.communication import Communication
from app.schemas.communication import CommunicationRead, SendMessageRequest
from app.services.communications import CommunicationService

router = APIRouter(prefix="/communications", tags=["communications"])


@router.get("", response_model=list[CommunicationRead])
def list_communications(db: DbSession, realtor: ActiveRealtor) -> list[Communication]:
    return db.query(Communication).filter(Communication.realtor_id == realtor.id).all()


@router.post("/send", response_model=CommunicationRead)
def send_message(payload: SendMessageRequest, db: DbSession, realtor: ActiveRealtor) -> Communication:
    row = CommunicationService(db).send_message(
        realtor=realtor,
        recipient=payload.recipient,
        channel=payload.channel.value,
        template=payload.template,
        context=payload.context,
        opportunity_id=payload.opportunity_id,
        transaction_id=payload.transaction_id,
        investor_id=payload.investor_id,
    )
    db.commit()
    db.refresh(row)
    return row
