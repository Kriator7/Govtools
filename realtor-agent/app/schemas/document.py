from uuid import UUID

from app.schemas.common import ORMModel


class DocumentGenerateRequest(ORMModel):
    template_name: str = "purchase_agreement"
    template_version: str | None = None


class DocumentRead(ORMModel):
    id: UUID
    public_id: str
    transaction_id: UUID
    document_type: str
    template_name: str
    template_version: str
    status: str
    review_required: bool
    generated_path: str | None = None
    content_hash: str | None = None
    missing_fields: list | None = None
    field_values: dict | None = None
    notes: str | None = None


class DocumentValidation(ORMModel):
    can_generate: bool
    missing_fields: list[str]
    present_fields: list[str]
    review_notice: str
