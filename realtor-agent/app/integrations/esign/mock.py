from typing import Any
from uuid import uuid4

from app.integrations.esign.base import SignatureProvider


class MockSignatureProvider(SignatureProvider):
    name = "mock"

    def __init__(self) -> None:
        self.envelopes: dict[str, dict[str, Any]] = {}

    def create_envelope(self, document_path: str, metadata: dict[str, Any]) -> dict[str, Any]:
        envelope_id = f"env-mock-{uuid4().hex[:10]}"
        self.envelopes[envelope_id] = {
            "envelope_id": envelope_id,
            "document_path": document_path,
            "metadata": metadata,
            "signers": [],
            "status": "created",
        }
        return self.envelopes[envelope_id]

    def add_signer(self, envelope_id: str, name: str, email: str, role: str) -> dict[str, Any]:
        envelope = self.envelopes[envelope_id]
        envelope["signers"].append({"name": name, "email": email, "role": role})
        return envelope

    def send_for_signature(self, envelope_id: str) -> dict[str, Any]:
        envelope = self.envelopes[envelope_id]
        envelope["status"] = "sent"
        return envelope

    def check_status(self, envelope_id: str) -> dict[str, Any]:
        return self.envelopes[envelope_id]

    def download_executed_document(self, envelope_id: str) -> bytes:
        return f"MOCK-EXECUTED:{envelope_id}".encode()
