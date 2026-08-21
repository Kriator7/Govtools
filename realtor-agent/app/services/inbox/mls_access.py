"""Detect Trestle / Cotality MLS API access mail and apply credentials to gitignored env.

Do not store secrets in the database. Do not put secrets in Telegram. Do not SMS Damian.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from app.config import PROJECT_ROOT
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
CLIENT_ID_RE = re.compile(r"client[_ -]?id\s*[:=]\s*['\"]?([A-Za-z0-9._\-]+)", re.I)
CLIENT_SECRET_RE = re.compile(r"client[_ -]?secret\s*[:=]\s*['\"]?(\S+)", re.I)
API_KEY_RE = re.compile(
    r"(?:api[_ -]?key|access[_ -]?key|subscription[_ -]?key|bearer(?:\s+token)?)\s*[:=]\s*['\"]?(\S+)",
    re.I,
)
DEFAULT_ODATA_URL = "https://api.cotality.com/trestle/odata/"
DEFAULT_TOKEN_URL = "https://api.cotality.com/trestle/oidc/connect/token"
LIVE_ACCESS_TEXT = (
    "We have live MLS access. Time to test.\n"
    "Trestle credentials were applied from email onto the gitignored env "
    "(not stored in the database, not posted here).\n"
    "I will not scrape Matrix. Relays stay on. I will not text Damian, Amos, or investors."
)
SKIP_CREDENTIAL_VALUES = {
    "plugin",
    "vendor",
    "here",
    "below",
    "required",
    "your",
    "xxxxx",
    "redacted",
}


def is_mls_api_access_mail(message: InboundMessage) -> bool:
    blob = _blob(message)
    subject = message.subject or ""
    if IDX_OPTIONS_ONLY_RE.search(blob) or re.search(r"idx options", subject, re.I):
        return False
    from_vendor = bool(
        re.search(
            r"trestle|cotality|corelogic\.com|trestlesupport|catalino|"
            r"lasvegasrealtor|las vegas realtor",
            message.from_header or "",
            re.I,
        )
    )
    if from_vendor:
        return True
    if re.search(r"\bpacket\s*(?:1|3|4|5|6|7|8|9|10)\b", subject, re.I):
        return False
    return bool(
        TRESTLE_SENDER_RE.search(blob)
        and ACCESS_HINT_RE.search(blob)
        and (
            CREDENTIAL_HINT_RE.search(blob)
            or ESIGN_HINT_RE.search(blob)
            or CONNECTED_HINT_RE.search(blob)
            or re.search(r"mlo connection", blob, re.I)
        )
    )


def mls_access_kind(message: InboundMessage) -> str:
    blob = _blob(message)
    if CREDENTIAL_HINT_RE.search(blob):
        return "credentials"
    if ESIGN_HINT_RE.search(blob):
        return "esign"
    if CONNECTED_HINT_RE.search(blob):
        return "connected"
    return "account"


def extract_mls_credentials(message: InboundMessage) -> dict[str, str]:
    if IDX_OPTIONS_ONLY_RE.search(_blob(message)) or re.search(r"idx options", message.subject or "", re.I):
        return {}
    blob = "\n".join(
        [
            message.body_text or "",
            *[
                item.data.decode("utf-8", errors="replace")
                for item in message.attachments
                if item.filename.lower().endswith((".txt", ".json", ".csv"))
            ],
        ]
    )
    found: dict[str, str] = {}
    for attachment in message.attachments:
        if not attachment.filename.lower().endswith(".json"):
            continue
        try:
            payload = json.loads(attachment.data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        mapping = {
            "client_id": ("client_id", "clientId", "clientid"),
            "client_secret": ("client_secret", "clientSecret", "clientsecret"),
            "api_key": ("api_key", "apiKey", "apikey", "access_token", "accessToken"),
        }
        for dest, keys in mapping.items():
            for key in keys:
                value = payload.get(key)
                if isinstance(value, str) and _usable_secret(value, minimum=8 if dest == "client_id" else 12):
                    found[dest] = value.strip().strip("'\"")
    match = CLIENT_ID_RE.search(blob)
    if match and _usable_secret(match.group(1), minimum=6):
        found["client_id"] = match.group(1).strip().strip("'\"")
    match = CLIENT_SECRET_RE.search(blob)
    if match and _usable_secret(match.group(1), minimum=12):
        found["client_secret"] = match.group(1).strip().strip("'\"")
    match = API_KEY_RE.search(blob)
    if match and _usable_secret(match.group(1), minimum=12):
        found["api_key"] = match.group(1).strip().strip("'\"")
    return found


def apply_mls_credentials(creds: dict[str, str], env_path: Path | None = None) -> dict:
    if not creds:
        return {"ok": False, "fields": []}
    path = env_path or (PROJECT_ROOT / ".env")
    updates = {
        "MLS_PROVIDER": "trestle",
        "MLS_API_BASE_URL": DEFAULT_ODATA_URL,
        "MLS_TOKEN_URL": DEFAULT_TOKEN_URL,
    }
    if creds.get("client_id"):
        updates["MLS_CLIENT_ID"] = creds["client_id"]
    if creds.get("client_secret"):
        updates["MLS_CLIENT_SECRET"] = creds["client_secret"]
    if creds.get("api_key"):
        updates["MLS_API_KEY"] = creds["api_key"]
    _upsert_dotenv(path, updates)
    os.environ["MLS_PROVIDER"] = "trestle"
    os.environ.setdefault("MLS_API_BASE_URL", DEFAULT_ODATA_URL)
    os.environ.setdefault("MLS_TOKEN_URL", DEFAULT_TOKEN_URL)
    if creds.get("client_id"):
        os.environ["MLS_CLIENT_ID"] = creds["client_id"]
    if creds.get("client_secret"):
        os.environ["MLS_CLIENT_SECRET"] = creds["client_secret"]
    if creds.get("api_key"):
        os.environ["MLS_API_KEY"] = creds["api_key"]
    from app.config import get_settings

    get_settings.cache_clear()
    return {"ok": True, "fields": sorted(updates), "provider": "trestle"}


def _usable_secret(value: str, *, minimum: int) -> bool:
    raw = str(value or "").strip().strip("'\"")
    if len(raw) < minimum:
        return False
    if raw.lower() in SKIP_CREDENTIAL_VALUES:
        return False
    if "plugin" in raw.lower() or "vendor" in raw.lower():
        return False
    return True


def _upsert_dotenv(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    found: set[str] = set()
    rewritten: list[str] = []
    for line in lines:
        match = re.match(r"^([A-Z0-9_]+)=(.*)$", line)
        if match and match.group(1) in updates:
            rewritten.append(f"{match.group(1)}={updates[match.group(1)]}")
            found.add(match.group(1))
        else:
            rewritten.append(line)
    if rewritten and rewritten[-1].strip():
        rewritten.append("")
    for key, value in updates.items():
        if key not in found:
            rewritten.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rewritten).rstrip() + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def format_mls_access_alert(message: InboundMessage, apply_result: dict | None = None) -> str:
    if (apply_result or {}).get("credentials_applied"):
        return LIVE_ACCESS_TEXT
    kind = mls_access_kind(message)
    kind_line = {
        "credentials": (
            "This looks like API credentials, but no usable key could be parsed. "
            "I did not change MLS_PROVIDER."
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
