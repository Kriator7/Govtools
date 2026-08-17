"""Provider-independent AI interface.

AI may summarize, explain, draft, and suggest. It must not sign contracts,
invent missing contractual values, change price, waive contingencies, submit
offers, impersonate the realtor, or issue final legal determinations.
"""

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    name: str = "ai"

    @abstractmethod
    def summarize_listing(self, listing: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def explain_match(self, explanation: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def draft_investor_message(self, context: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def suggest_criteria(self, natural_language: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def brief_realtor(self, context: dict[str, Any]) -> str:
        raise NotImplementedError
