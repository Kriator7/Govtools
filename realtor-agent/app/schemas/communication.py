from uuid import UUID

from app.models.enums import InvestorResponse, NotificationChannel
from app.schemas.common import ORMModel


class SendMessageRequest(ORMModel):
    channel: NotificationChannel
    template: str
    recipient: str
    context: dict
    opportunity_id: UUID | None = None
    transaction_id: UUID | None = None
    investor_id: UUID | None = None


class CommunicationRead(ORMModel):
    id: UUID
    public_id: str
    channel: str
    template: str | None
    direction: str
    recipient: str
    body: str
    status: str
    response_value: str | None = None
    provider_message_id: str | None = None


class InvestorReply(ORMModel):
    response: InvestorResponse
    body: str | None = None
