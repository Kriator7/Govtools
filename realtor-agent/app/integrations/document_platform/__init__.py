"""Placeholder for a future transaction-management platform adapter."""

from app.integrations.document_platform.base import DocumentPlatformProvider
from app.integrations.document_platform.mock import MockDocumentPlatformProvider

__all__ = ["DocumentPlatformProvider", "MockDocumentPlatformProvider"]
