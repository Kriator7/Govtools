"""E-signature / transaction-platform abstraction.

Implement a vendor adapter only after the realtor's existing platform is
identified and an approved integration path exists. The application must never
sign or submit contractual documents without explicit realtor approval.
"""

from abc import ABC, abstractmethod
from typing import Any


class SignatureProvider(ABC):
    name: str = "esign"

    @abstractmethod
    def create_envelope(self, document_path: str, metadata: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def add_signer(self, envelope_id: str, name: str, email: str, role: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def send_for_signature(self, envelope_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def check_status(self, envelope_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def download_executed_document(self, envelope_id: str) -> bytes:
        raise NotImplementedError
