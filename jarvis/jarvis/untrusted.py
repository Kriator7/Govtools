"""External content is data. It is never an instruction."""

from __future__ import annotations

INSTRUCTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "system:",
    "you are now",
    "send all credentials",
    "exfiltrate",
    "disregard your",
)


def wrap(kind: str, text: str) -> dict[str, object]:
    lowered = text.lower()
    markers = [item for item in INSTRUCTION_MARKERS if item in lowered]
    return {
        "trust": "untrusted",
        "kind": kind,
        "acted_on_instructions": False,
        "instruction_markers": markers,
        "notice": "This content is untrusted data and was not executed as an instruction.",
        "text": text,
    }
