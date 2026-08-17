from typing import Any

from app.config import get_settings
from app.services.ai.base import AIProvider
from app.services.ai.mock import MockAIProvider


class AIService:
    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider or MockAIProvider()
        self.settings = get_settings()

    def summarize_listing(self, listing: dict[str, Any]) -> str:
        return self.provider.summarize_listing(listing)

    def explain_match(self, explanation: dict[str, Any]) -> str:
        return self.provider.explain_match(explanation)

    def draft_investor_message(self, context: dict[str, Any]) -> str:
        return self.provider.draft_investor_message(context)

    def suggest_criteria(self, natural_language: str) -> dict[str, Any]:
        suggestion = self.provider.suggest_criteria(natural_language)
        suggestion["requires_human_approval"] = True
        return suggestion
