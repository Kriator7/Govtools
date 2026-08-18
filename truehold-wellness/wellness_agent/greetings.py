"""Detect salutations that start the TrueHold Wellness introduction."""

from __future__ import annotations

import re
import unicodedata

# First-visit greetings. Word-boundary matched so "high" / "this" do not fire.
SALUTATIONS = (
    "hello",
    "hello there",
    "hi",
    "hi there",
    "hey",
    "hey there",
    "heya",
    "hiya",
    "howdy",
    "yo",
    "sup",
    "what's up",
    "whats up",
    "what up",
    "good morning",
    "good afternoon",
    "good evening",
    "good night",
    "morning",
    "afternoon",
    "evening",
    "greetings",
    "hola",
    "how are you",
    "how's it going",
    "hows it going",
    "how goes it",
    "nice to meet you",
)

_GREETING_RE = re.compile(
    r"^(?:👋|🙋|)\s*(?:%s)\b" % "|".join(re.escape(item) for item in sorted(SALUTATIONS, key=len, reverse=True)),
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text or "")
    folded = folded.replace("’", "'").replace("‘", "'")
    folded = re.sub(r"[!?.,;:~]+", " ", folded.lower())
    return " ".join(folded.split())


def is_salutation(text: str) -> bool:
    """True when the message is (or starts with) a greeting."""
    normalized = _normalize(text)
    if not normalized:
        return False
    if normalized in {"👋", "🙋"}:
        return True
    return _GREETING_RE.match(normalized) is not None
