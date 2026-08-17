from typing import Any
from uuid import uuid4

from app.integrations.document_platform.base import DocumentPlatformProvider


class MockDocumentPlatformProvider(DocumentPlatformProvider):
    name = "mock"

    def submit_document(self, transaction_public_id: str, document_path: str) -> dict[str, Any]:
        return {
            "submission_id": f"plat-mock-{uuid4().hex[:10]}",
            "transaction_public_id": transaction_public_id,
            "document_path": document_path,
            "status": "accepted_for_review",
        }
