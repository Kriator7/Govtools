"""Strip credentials that must never be stored from inbound packet mail."""

from __future__ import annotations

import re

SECRET_LINE = re.compile(
    r"(?im)^(.*\b(?:password|passwd|passcode|app password|secret|api[_ ]?key|auth[_ ]?token|"
    r"access[_ ]?token|twilio[_ ]?(?:auth_)?token|bot[_ ]?token|client[_ -]?secret|"
    r"client[_ -]?id|consumer[_ -]?secret|refresh[_ -]?token)\b\s*[:=]\s*)(\S+.*)$"
)
SECRET_INLINE = re.compile(
    r"(?i)\b((?:password|secret|api[_ ]?key|auth[_ ]?token|app password|client[_ -]?secret|"
    r"client[_ -]?id|consumer[_ -]?secret)\s*[:=]\s*)(\S+)"
)


def redact_text(text: str | None) -> str:
    if not text:
        return ""
    redacted = SECRET_LINE.sub(r"\1[REDACTED — not stored; share via password manager]", text)
    return SECRET_INLINE.sub(r"\1[REDACTED]", redacted)


def looks_like_secret_filename(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in ("password", "secret", "credentials", "app-password"))
