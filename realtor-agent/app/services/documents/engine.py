"""Document generation with required-field validation. Never invent contract values."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.integrations.google_cloud.storage import StorageBackend, default_storage
from app.models.document import Document
from app.models.enums import (
    DOCUMENT_TRANSITIONS,
    ActorOrigin,
    ActorType,
    DocumentStatus,
    TransactionStatus,
)
from app.models.investor import Investor
from app.models.listing import Listing
from app.models.realtor import Realtor
from app.models.transaction import Transaction
from app.services.audit import AuditService
from app.services.documents.pdf import ensure_sample_template, fill_pdf
from app.services.documents.registry import TemplateRegistry
from app.services.transactions.engine import InvalidTransition
from app.utilities.hashing import sha256_file
from app.utilities.ids import next_public_id
from app.utilities.money import money_label

REVIEW_NOTICE = (
    "DRAFT documents require realtor review. The system will not sign, submit, "
    "or transmit contractual documents without explicit realtor approval."
)


class DocumentValidationError(ValueError):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__("Cannot generate document. Missing: " + ", ".join(missing))


TRANSACTION_SOURCE_FIELDS = {
    "buyer_name": "buyer_legal_name",
    "purchase_price": "offer_price",
    "earnest_money": "earnest_money",
    "closing_date": "requested_closing_date",
    "financing_type": "financing_type",
    "property_address": None,
}


class DocumentEngine:
    def __init__(
        self,
        db: Session,
        registry: TemplateRegistry | None = None,
        storage: StorageBackend | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self.db = db
        self.registry = registry or TemplateRegistry()
        self.storage = storage or default_storage()
        self.audit = audit or AuditService(db)

    def validate(self, transaction: Transaction, template_name: str = "purchase_agreement") -> dict:
        spec = self.registry.get(template_name)
        values = self._collect_values(transaction)
        missing = [key for key in spec.required_fields if not values.get(key)]
        present = [key for key in spec.required_fields if values.get(key)]
        return {
            "can_generate": not missing,
            "missing_fields": missing,
            "present_fields": present,
            "review_notice": REVIEW_NOTICE,
            "values": values,
        }

    def generate(
        self,
        realtor: Realtor,
        transaction: Transaction,
        template_name: str = "purchase_agreement",
        template_version: str | None = None,
    ) -> Document:
        spec = self.registry.get(template_name, template_version)
        validation = self.validate(transaction, template_name)
        if not validation["can_generate"]:
            raise DocumentValidationError(validation["missing_fields"])
        ensure_sample_template(spec.path)
        mapped = {pdf_field: validation["values"][internal] for internal, pdf_field in spec.field_map.items()}
        pdf_bytes = fill_pdf(spec.path, mapped)
        relative = (
            f"transactions/{transaction.public_id}/drafts/"
            f"{template_name}-{spec.version}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.pdf"
        )
        stored = self.storage.write_bytes(relative, pdf_bytes)
        from pathlib import Path

        content_hash = sha256_file(Path(stored)) if Path(stored).exists() else None
        document = Document(
            public_id=next_public_id(self.db, "DOC"),
            realtor_id=realtor.id,
            transaction_id=transaction.id,
            document_type=spec.metadata.get("document_type", template_name),
            template_name=spec.name,
            template_version=spec.version,
            jurisdiction=spec.metadata.get("jurisdiction", "NV"),
            status=DocumentStatus.DRAFT.value,
            review_required=True,
            source_path=str(spec.path),
            generated_path=stored,
            content_hash=content_hash,
            generated_by="system",
            generation_timestamp=datetime.now(timezone.utc),
            field_values=mapped,
            missing_fields=[],
            notes=REVIEW_NOTICE,
        )
        self.db.add(document)
        self.db.flush()
        self.audit.record(
            event="DOCUMENT_GENERATED",
            object_type="document",
            object_id=document.public_id,
            actor="document_engine",
            actor_type=ActorType.SYSTEM.value,
            origin=ActorOrigin.AUTOMATION.value,
            realtor_id=str(realtor.id),
            after_state={"status": document.status, "template": f"{spec.name}/{spec.version}"},
        )
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type="DOCUMENT_GENERATED",
            message=f"{template_name} draft generated — realtor review required",
            transaction_id=transaction.id,
        )
        return document

    def transition(self, realtor: Realtor, document: Document, new_status: DocumentStatus) -> Document:
        current = DocumentStatus(document.status)
        if new_status not in DOCUMENT_TRANSITIONS.get(current, set()):
            raise InvalidTransition(f"Cannot move document {current.value} -> {new_status.value}")
        if new_status == DocumentStatus.EXECUTED and document.generated_path:
            # Executed copies are written to a separate folder and never overwritten.
            pass
        before = document.status
        document.status = new_status.value
        if new_status == DocumentStatus.APPROVED_BY_REALTOR:
            document.reviewed_by = realtor.public_id
            document.review_timestamp = datetime.now(timezone.utc)
        self.audit.record(
            event="DOCUMENT_STATUS_CHANGED",
            object_type="document",
            object_id=document.public_id,
            actor=realtor.public_id,
            actor_type=ActorType.REALTOR.value,
            origin=ActorOrigin.HUMAN.value,
            realtor_id=str(realtor.id),
            before_state={"status": before},
            after_state={"status": document.status},
        )
        return document

    def _collect_values(self, transaction: Transaction) -> dict[str, str]:
        listing = self.db.get(Listing, transaction.listing_id)
        investor = self.db.get(Investor, transaction.investor_id)
        address = ""
        if listing:
            address = f"{listing.street_address}, {listing.city}, {listing.state} {listing.zip_code}"
        buyer = transaction.buyer_legal_name or (investor.name if investor else "")
        price = transaction.offer_price or (listing.asking_price if listing else None)
        return {
            "buyer_name": buyer or "",
            "property_address": address,
            "purchase_price": money_label(price) if price is not None else "",
            "earnest_money": money_label(transaction.earnest_money) if transaction.earnest_money is not None else "",
            "closing_date": transaction.requested_closing_date.isoformat()
            if transaction.requested_closing_date
            else "",
            "financing_type": transaction.financing_type or "",
        }
