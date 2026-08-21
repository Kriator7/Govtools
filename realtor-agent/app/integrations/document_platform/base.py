from abc import ABC, abstractmethod
from typing import Any


class DocumentPlatformProvider(ABC):
    name: str = "document_platform"

    @abstractmethod
    def submit_document(self, transaction_public_id: str, document_path: str) -> dict[str, Any]:
        raise NotImplementedError
