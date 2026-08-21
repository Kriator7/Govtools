"""Gmail IMAP client for Damian packet replies.

IMAP/SMTP: https://developers.google.com/workspace/gmail/imap/imap-smtp
App passwords: https://support.google.com/accounts/answer/185833
"""

from __future__ import annotations

import imaplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.services.inbox.message import InboundMessage, parse_rfc822
from app.services.seed import DAMIAN_EMAIL

GMAIL_PACKET_QUERY = (
    f"(einbinder OR damian OR from:{DAMIAN_EMAIL} OR from:thehomefinderlv.com "
    'OR "home finder" OR homefinder OR thehomefinderlv '
    "OR catalino OR trestle OR cotality OR corelogic "
    'OR from:cotality.com OR from:corelogic.com OR from:trestle.corelogic.com '
    'OR "las vegas realtor" OR lasvegasrealtor OR idx OR webapi OR "web api" '
    'OR "mlo connection" OR "technology provider" OR "data license" '
    'OR "api key" OR "client secret" OR "client id" '
    'OR "packet 1" OR "packet 2" OR "packet 3" OR "packet 4" OR "packet 5" '
    'OR "packet 6" OR "packet 7" OR "packet 8" OR "packet 9" OR "packet 10" '
    'OR "buy box" OR "investor list")'
)


@dataclass(frozen=True)
class ImapAccount:
    username: str
    password: str
    host: str = "imap.gmail.com"
    port: int = 993
    mailbox: str = "INBOX"
    label: str = ""

    @property
    def name(self) -> str:
        return self.label or self.username


class MessageSource(Protocol):
    def fetch(self, account: ImapAccount, *, lookback_days: int) -> list[InboundMessage]: ...


class ImapMessageSource:
    def fetch(self, account: ImapAccount, *, lookback_days: int) -> list[InboundMessage]:
        context = ssl.create_default_context()
        client = imaplib.IMAP4_SSL(account.host, account.port, ssl_context=context)
        try:
            client.login(account.username, account.password.replace(" ", ""))
            client.select(account.mailbox, readonly=True)
            uids = _search_uids(client, lookback_days)
            messages: list[InboundMessage] = []
            for uid in uids:
                typ, data = client.uid("FETCH", uid, "(BODY.PEEK[])")
                if typ != "OK" or not data:
                    continue
                raw = _rfc822_from_fetch(data)
                if not raw:
                    continue
                messages.append(parse_rfc822(raw, account=account.name, uid=uid.decode() if isinstance(uid, bytes) else str(uid)))
            return messages
        finally:
            try:
                client.logout()
            except Exception:  # noqa: BLE001
                pass


def _search_uids(client: imaplib.IMAP4, lookback_days: int) -> list[bytes]:
    newer = max(1, int(lookback_days))
    raw_query = f"newer_than:{newer}d {GMAIL_PACKET_QUERY}"
    try:
        typ, data = client.uid("SEARCH", "X-GM-RAW", raw_query)
        if typ == "OK" and data and data[0]:
            return data[0].split()
    except Exception:  # noqa: BLE001
        pass
    since = (datetime.now(timezone.utc) - timedelta(days=newer)).strftime("%d-%b-%Y")
    found: list[bytes] = []
    for criteria in (
        ("SINCE", since, "FROM", "einbinder"),
        ("SINCE", since, "FROM", "homefinder"),
        ("FROM", DAMIAN_EMAIL),
        ("FROM", "thehomefinderlv.com"),
        ("SINCE", since, "FROM", "cotality.com"),
        ("SINCE", since, "FROM", "corelogic.com"),
        ("SINCE", since, "FROM", "trestle"),
        ("SINCE", since, "FROM", "catalino"),
        ("SINCE", since, "SUBJECT", "Trestle"),
        ("SINCE", since, "SUBJECT", "MLO"),
        ("SINCE", since, "SUBJECT", "WebAPI"),
    ):
        try:
            typ, data = client.uid("SEARCH", None, *criteria)
        except Exception:  # noqa: BLE001
            continue
        if typ == "OK" and data and data[0]:
            found.extend(data[0].split())
    # Preserve order, drop duplicates.
    unique: list[bytes] = []
    seen: set[bytes] = set()
    for uid in found:
        if uid not in seen:
            seen.add(uid)
            unique.append(uid)
    return unique


def _rfc822_from_fetch(data) -> bytes:
    chunks: list[bytes] = []
    for part in data:
        if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], (bytes, bytearray)):
            chunks.append(bytes(part[1]))
    return b"".join(chunks)
