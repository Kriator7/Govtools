"""Standing TrueHold Wellness discounts. Staff-approved; never invent other sales.

TrueHold Wellness only. Not realtor-agent.
"""

from __future__ import annotations

import re

COLLEGE_CODE = "ADPILV2026"
COLLEGE_PERCENT = 10
COLLEGE_AUDIENCE = "college students"

COLLEGE_POLICY = (
    f"College students get {COLLEGE_PERCENT}% off with discount code {COLLEGE_CODE}. "
    "Send the code in this chat. The team applies it on the confirmation call. "
    "The floor team never invents any other sale."
)

COLLEGE_THANKS = (
    f"<b>College discount</b>\n"
    f"Got it — {COLLEGE_CODE} is on this chat for {COLLEGE_PERCENT}% off.\n"
    "College students only. The team will apply it when they call to confirm."
)

COLLEGE_HELP = (
    f"College students: {COLLEGE_PERCENT}% off with code {COLLEGE_CODE}. "
    "Send that code here before you order."
)

_CODE_RE = re.compile(r"\bADPILV2026\b", re.IGNORECASE)


def extract_code(text: str) -> str | None:
    if _CODE_RE.search(text or ""):
        return COLLEGE_CODE
    return None


def strip_code(text: str) -> str:
    cleaned = _CODE_RE.sub(" ", text or "")
    return " ".join(cleaned.split())


_FILLER = {
    "code",
    "discount",
    "promo",
    "coupon",
    "please",
    "thanks",
    "thank",
    "you",
    "the",
    "a",
    "my",
    "for",
    "college",
    "student",
    "students",
    "here",
    "is",
    "this",
}


def is_code_only_message(text: str) -> bool:
    leftover = re.sub(r"[.!,?]", " ", strip_code(text)).lower().lstrip("/")
    tokens = leftover.split()
    return all(tok in _FILLER for tok in tokens)


def staff_discount_line(code: str | None) -> str:
    if not code:
        return ""
    return (
        f"Discount: {code} — {COLLEGE_PERCENT}% off ({COLLEGE_AUDIENCE}). "
        "Apply on the confirmation call."
    )


def customer_discount_line(code: str | None) -> str:
    if not code:
        return ""
    return f"{COLLEGE_PERCENT}% off code {code} is on file for this chat (college students)."
