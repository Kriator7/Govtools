"""Decide whether inbound mail is a Damian packet reply, and which packets it fills."""

from __future__ import annotations

import re

from app.services.inbox.message import InboundMessage

from app.services.seed import DAMIAN_EMAIL

DAMIAN_SENDER_NEEDLES = (
    "einbinder",
    "home finder",
    "homefinder",
    "homefinderrealty",
    "thehomefinderlv",
    DAMIAN_EMAIL,
)

MLS_ASSOCIATION_SENDER_NEEDLES = (
    "catalino",
    "las vegas realtor",
    "lasvegasrealtor",
    "glvar",
    "trestle.corelogic.com",
    "cotality.com",
)

IGNORE_SENDER_NEEDLES = (
    "zillow.com",
    "zillowgroup",
    "trulia.com",
    "realtor.com",
    "redfin.com",
    "linkedin.com",
    "meetup.com",
    "notifications.tiktok.com",
    "noreply-tt4b",
    "mail.house.gov",
)

CALENDAR_IGNORE = re.compile(
    r"has accepted this invitation|invitation from google calendar|text/calendar|"
    r"^accepted:",
    re.I,
)

QUOTED_SPLIT = re.compile(
    r"(?im)^On .+wrote:\s*$|^---------- Forwarded message",
)

PACKET_PATTERNS = {
    1: re.compile(r"\bpacket\s*1\b|who you are|license number|brokerage legal name", re.I),
    2: re.compile(
        r"\bpacket\s*2\b|listing access|\bmls agent\b|glvar|reso web api|\bidx\b|trestle|"
        r"matrix|cotality|catalino|las vegas realtor",
        re.I,
    ),
    3: re.compile(r"\bpacket\s*3\b|investor list|investor clientele", re.I),
    4: re.compile(r"\bpacket\s*4\b|buy box|acquisition profile|investor criteria", re.I),
    5: re.compile(
        r"\bpacket\s*5\b|telegram as the command center|alert hours|minimum match score",
        re.I,
    ),
    6: re.compile(r"\bpacket\s*6\b|twilio|tcpa|investor text|notify investors", re.I),
    7: re.compile(r"\bpacket\s*7\b|purchase agreement|addenda|disclosure form", re.I),
    8: re.compile(
        r"\bpacket\s*8\b|e-sign platform|transaction platform|who must sign|"
        r"who is allowed to press send",
        re.I,
    ),
    9: re.compile(r"\bpacket\s*9\b|sample closed|closed investor deal", re.I),
    10: re.compile(r"\bpacket\s*10\b|earnest money|inspection days|office rules", re.I),
}

IDENTITY_HINT = re.compile(
    r"(?im)^(?:full legal name|legal name|brokerage|nevada license|license number|"
    r"mobile phone|work email|timezone)\s*[:=]"
)


def is_ignored_sender(message: InboundMessage) -> bool:
    blob = f"{message.from_header} {message.to_header}".lower()
    return any(needle in blob for needle in IGNORE_SENDER_NEEDLES)


def is_calendar_noise(message: InboundMessage) -> bool:
    haystack = f"{message.subject}\n{message.body_text[:800]}"
    return bool(CALENDAR_IGNORE.search(haystack))


def reply_body(text: str | None) -> str:
    """Keep Damian's reply; drop Gmail quoted checklist and forwards."""
    if not text:
        return ""
    return QUOTED_SPLIT.split(text, maxsplit=1)[0].strip()


def is_damian_sender(message: InboundMessage) -> bool:
    blob = f"{message.from_header} {message.subject}".lower()
    return any(needle in blob for needle in DAMIAN_SENDER_NEEDLES)


def is_mls_association_sender(message: InboundMessage) -> bool:
    blob = f"{message.from_header} {message.subject} {message.body_text[:1500]}".lower()
    return any(needle in blob for needle in MLS_ASSOCIATION_SENDER_NEEDLES)


def is_packet_candidate(
    message: InboundMessage,
    watch_address: str = "",
    extra_from: tuple[str, ...] | list[str] = (),
) -> bool:
    if is_ignored_sender(message):
        return False
    if is_calendar_noise(message):
        return False
    if is_damian_sender(message) or is_mls_association_sender(message):
        return True
    from_header = message.from_header.lower()
    return any(email and email.lower() in from_header for email in extra_from)


def classify_packets(message: InboundMessage) -> list[int]:
    haystack = "\n".join(
        [
            message.subject,
            reply_body(message.body_text),
            " ".join(item.filename for item in message.attachments),
        ]
    )
    found = [number for number, pattern in PACKET_PATTERNS.items() if pattern.search(haystack)]
    names = [item.filename.lower() for item in message.attachments]
    tabular = [name for name in names if name.endswith((".csv", ".xlsx", ".xlsm", ".xls"))]
    if tabular:
        investor_sheet = any(
            re.search(r"investor|clientele|buy.?box|criteria|profile", name, re.I) for name in tabular
        ) or re.search(r"investor list|investor clientele|packet\s*3|packet\s*4", haystack, re.I)
        if investor_sheet and 3 not in found:
            found.append(3)
        if 4 not in found and re.search(r"criteria|buy.?box|profile", haystack, re.I):
            found.append(4)
        elif 4 not in found and investor_sheet and re.search(
            r"min(?:imum)? price|cities|zip|property type", haystack, re.I
        ):
            found.append(4)
    if IDENTITY_HINT.search(reply_body(message.body_text)) and 1 not in found:
        found.append(1)
    return sorted(set(found))
