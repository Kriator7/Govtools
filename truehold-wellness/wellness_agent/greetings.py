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


_CREW_RE = re.compile(
    r"(?:let'?s|lets|let us|see|show|meet|who is|who'?s|where'?s|where is).{0,32}\b"
    r"(crew|class photo|group photo|everyone|whole (?:floor )?team)\b"
    r"|\b(the crew|floor crew|class photo|group photo|office photo)\b",
    re.IGNORECASE,
)


def is_crew_request(text: str) -> bool:
    """True when the customer asked to see the whole floor-team class photo."""
    normalized = _normalize(text)
    if not normalized:
        return False
    if normalized in {"crew", "the crew", "floor crew", "class photo", "group photo", "office photo"}:
        return True
    return _CREW_RE.search(normalized) is not None


_CREED_RE = re.compile(
    r"\b("
    r"why (?:are|do) you|what do you (?:believe|stand|care)|your mission|"
    r"truehold(?: wellness)? (?:why|mission|believe)|"
    r"empower(?:ment)?|take control|ownership|"
    r"natur(?:e|al|ally)|god|bone broth|ferment|"
    r"vitamin\s*c|oranges?|hostage|oxygen|"
    r"already (?:in|exist)|naturally occurring|"
    r"people deserve|profiteer|the truth|tell others|"
    r"quote|who said|emerson|paracelsus|lind|nightingale|muir|"
    r"why peptides|why this (?:house|bot|shop)"
    r")\b",
    re.IGNORECASE,
)


def is_creed_request(text: str) -> bool:
    """True when the customer asked why this house exists or what we believe."""
    normalized = _normalize(text)
    if not normalized:
        return False
    return _CREED_RE.search(normalized) is not None


_BIO_RE = re.compile(
    r"\b("
    r"who are you|your bio|about you|tell me about you|"
    r"who is (?:theo|lumen|mira|sol|nova|reed|lila|kai|sage|vega|orion|wynn|indi|pax|ember|quinn|nori|dash|halo|rio|true)|"
    r"floor team|your experience|how long have you|clinical experience"
    r")\b",
    re.IGNORECASE,
)


def is_bio_request(text: str) -> bool:
    normalized = _normalize(text)
    return bool(normalized and _BIO_RE.search(normalized))


_FASTING_RE = re.compile(
    r"\b("
    r"fast(?:ing|ed)?|eating window|16\s*:\s*8|time restricted|"
    r"intermittent|skip(?:ping)? breakfast"
    r")\b",
    re.IGNORECASE,
)


def is_fasting_request(text: str) -> bool:
    normalized = _normalize(text)
    return bool(normalized and _FASTING_RE.search(normalized))


_HERB_RE = re.compile(
    r"\b("
    r"herb|herbs|ginger|peppermint|chamomile|turmeric|cinnamon|"
    r"dandelion|lemon balm|fennel|nettle|bone broth|broth|"
    r"homeopath|remed(?:y|ies)|kitchen ally|tea"
    r")\b",
    re.IGNORECASE,
)


def is_herb_request(text: str) -> bool:
    normalized = _normalize(text)
    return bool(normalized and _HERB_RE.search(normalized))


_FASTING_YES_RE = re.compile(r"\b(yes|yeah|yep|yup|i have|i've|i fast)\b", re.I)
_FASTING_NO_RE = re.compile(r"\b(no|nope|not yet|never|haven't|have not)\b", re.I)


def fasting_answer(text: str) -> bool | None:
    """True/False when the message is a yes/no to the fasting opener."""
    normalized = _normalize(text)
    if not normalized:
        return None
    if _FASTING_YES_RE.search(normalized) and not _FASTING_NO_RE.search(normalized):
        return True
    if _FASTING_NO_RE.search(normalized):
        return False
    return None


def is_salutation(text: str) -> bool:
    """True when the message is (or starts with) a greeting."""
    normalized = _normalize(text)
    if not normalized:
        return False
    if normalized in {"👋", "🙋"}:
        return True
    return _GREETING_RE.match(normalized) is not None
