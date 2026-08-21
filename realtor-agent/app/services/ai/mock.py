from typing import Any

from app.services.ai.base import AIProvider


class MockAIProvider(AIProvider):
    name = "mock"

    def summarize_listing(self, listing: dict[str, Any]) -> str:
        address = listing.get("street_address", "the property")
        city = listing.get("city", "")
        price = listing.get("asking_price", "")
        remarks = (listing.get("remarks") or "No public remarks provided.").strip()
        return f"{address}, {city} listed at {price}. Remarks: {remarks[:240]}"

    def explain_match(self, explanation: dict[str, Any]) -> str:
        reasons = "; ".join(explanation.get("reasons") or [])
        issues = "; ".join(explanation.get("potential_issues") or []) or "none"
        return (
            f"Score {explanation.get('match_score')} ({explanation.get('category')}). "
            f"Reasons: {reasons}. Potential issues: {issues}."
        )

    def draft_investor_message(self, context: dict[str, Any]) -> str:
        return (
            f"New property opportunity:\n"
            f"{context.get('address')}\n"
            f"{context.get('city')}, {context.get('state')} {context.get('zip_code')}\n"
            f"Price: {context.get('price')}\n"
            f"{context.get('beds')} Bed / {context.get('baths')} Bath\n"
            f"{context.get('sqft')} sq ft\n"
            f"This appears to match your current {context.get('profile_name', 'acquisition')} criteria.\n"
            f"Interested?\nYES\nNO\nMORE INFO"
        )

    def suggest_criteria(self, natural_language: str) -> dict[str, Any]:
        return {
            "suggested": True,
            "requires_human_approval": True,
            "source_text": natural_language,
            "note": "Suggestions only. Do not apply automatically.",
        }

    def brief_realtor(self, context: dict[str, Any]) -> str:
        return (
            f"Briefing for {context.get('address')}: score {context.get('score')} "
            f"for {context.get('investor')}. Draft only — realtor approval required."
        )
