"""Detect Trestle / Cotality MLS API access mail. Do not store secrets. Do not SMS Damian."""

from __future__ import annotations

import re

from app.services.inbox.classify import is_mls_association_sender
from app.services.inbox.message import InboundMessage
from app.services.inbox.redact import redact_text

TRESTLE_SENDER_RE = re.compile(
    r"trestle|cotality|corelogic\.com|trestlesupport|catalino|las vegas realtor|"
    r"lasvegasrealtor",
    re.I,
)
ACCESS_HINT_RE = re.compile(
    r"mlo connection|data license|license agreement|please (?:review and )?sign|"
    r"client[_ -]?id|client[_ -]?secret|api credential|access (?:has been )?granted|"
    r"subscription (?:is )?active|connected to|technology provider|"
    r"onboarding|oauth|web\s*api|webapi|api access|verify your (?:email|account)|"
    r"welcome to trestle|docu\s*sign",
    re.I,
)
IDX_OPTIONS_ONLY_RE = re.compile(
    r"options for obtaining idx|do not choose 2 and 3|do not choose option 2 and option 3",
    re.I,
)
CREDENTIAL_HINT_RE = re.compile(
    r"client[_ -]?secret|client[_ -]?id|api[_ -]?key|consumer[_ -]?secret|oauth",
    re.I,
)
ESIGN_HINT_RE = re.compile(r"please (?:review and )?sign|docu\s*sign|e-?sign|ratif", re.I)
CONNECTED_HINT_RE = re.compile(
    r"access (?:has been )?granted|subscription (?:is )?active|connection (?:is )?approved|"
    r"connected to",
    re.I,
)


def is_mls_api_access_mail(message: InboundMessage) -> bool:
    blob = _blob(message)
    if IDX_OPTIONS_ONLY_RE.search(blob) and not CREDENTIAL_HINT_RE.search(blob) and not CONNECTED_HINT_RE.search(blob):
        return False
    if TRESTLE_SENDER_RE.search(f"{message.from_header} {message.subject}"):
        return True
    if is_mls_association_sender(message) and ACCESS_HINT_RE.search(blob):
        return True
    return bool(TRESTLE_SENDER_RE.search(blob) and ACCESS_HINT_RE.search(blob))


def mls_access_kind(message: InboundMessage) -> str:
    blob = _blob(message)
    if CREDENTIAL_HINT_RE.search(blob):
        return "credentials"
    if ESIGN_HINT_RE.search(blob):
        return "esign"
    if CONNECTED_HINT_RE.search(blob):
        return "connected"
    return "account"


def format_mls_access_alert(message: InboundMessage, apply_result: dict | None = None) -> str:
    kind = mls_access_kind(message)
    kind_line = {
        "credentials": (
            "This looks like API credentials. They were redacted and not stored. "
            "Put them in the gitignored .env / secret manager when you want live MLS. "
            "MLS_PROVIDER stays mock until then."
        ),
        "esign": (
            "This looks like an e-sign / MLO connection step. Damian or the broker "
            "still has to sign the Las Vegas REALTORS connection. I will not text them."
        ),
        "connected": (
            "This looks like a connection/approval notice. Live MLS stays disconnected "
            "until Trestle credentials exist in env/secret manager."
        ),
        "account": (
            "This looks like a Trestle/Cotality account or access message. "
            "Waiting for the Las Vegas REALTORS MLO connection + credentials."
        ),
    }[kind]
    status = (apply_result or {}).get("status") or "recorded"
    return (
        "MLS API access mail arrived (Packet 2).\n"
        f"From: {redact_text(message.from_header)}\n"
        f"Subject: {redact_text(message.subject)}\n"
        f"Inbox apply: {status}.\n"
        f"{kind_line}\n"
        "I will not scrape Matrix. Relays stay on. I will not text Damian, Amos, or investors."
    )


def _blob(message: InboundMessage) -> str:
    return f"{message.from_header}\n{message.subject}\n{message.body_text[:4000]}"
