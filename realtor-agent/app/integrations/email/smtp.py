"""SMTP email sender. Gmail uses smtp.gmail.com:587 + STARTTLS and an App Password.

Docs:
- SMTP: https://developers.google.com/workspace/gmail/imap/imap-smtp
- App passwords: https://support.google.com/accounts/answer/185833
- Device/app SMTP: https://support.google.com/a/answer/176600
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any
from uuid import uuid4

from app.integrations.email.base import EmailProvider


class SmtpEmailProvider(EmailProvider):
    name = "smtp"

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        *,
        starttls: bool = True,
    ) -> None:
        if not host or not username or not password:
            raise ValueError("EMAIL_SMTP_HOST, EMAIL_SMTP_USERNAME, and EMAIL_SMTP_PASSWORD are required")
        self.host = host
        self.port = port
        self.username = username
        self.password = password.replace(" ", "")
        self.starttls = starttls

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        *,
        from_address: str,
        reply_to: str | None = None,
        intended_recipient: str | None = None,
    ) -> dict[str, Any]:
        message = EmailMessage()
        message["From"] = from_address
        message["To"] = to
        message["Subject"] = subject
        if reply_to:
            message["Reply-To"] = reply_to
        if intended_recipient and intended_recipient != to:
            message["X-Intended-Recipient"] = intended_recipient
            body = (
                f"[TEST RELAY] Intended recipient: {intended_recipient}\n"
                f"Delivered to relay inbox: {to}\n\n"
                f"{body}"
            )
        message.set_content(body)
        with self._client() as smtp:
            smtp.send_message(message)
        return {
            "provider_message_id": f"smtp-{uuid4().hex[:12]}",
            "from": from_address,
            "to": to,
            "reply_to": reply_to,
            "intended_recipient": intended_recipient,
            "subject": subject,
            "status": "sent",
        }

    def health(self) -> tuple[str, str]:
        try:
            with self._client() as smtp:
                smtp.noop()
            return ("ok", f"smtp login succeeded at {self.host}:{self.port}")
        except Exception as exc:  # noqa: BLE001
            return ("error", str(exc))

    def _client(self):
        return _SmtpSession(self.host, self.port, self.username, self.password, self.starttls)


class _SmtpSession:
    def __init__(self, host: str, port: int, username: str, password: str, starttls: bool) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.starttls = starttls
        self._smtp: smtplib.SMTP | None = None

    def __enter__(self) -> smtplib.SMTP:
        if self.port == 465 and not self.starttls:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(self.host, self.port, timeout=20)
        else:
            smtp = smtplib.SMTP(self.host, self.port, timeout=20)
            smtp.ehlo()
            if self.starttls:
                smtp.starttls()
                smtp.ehlo()
        smtp.login(self.username, self.password)
        self._smtp = smtp
        return smtp

    def __exit__(self, exc_type, exc, tb) -> None:
        smtp = self._smtp
        if smtp is None:
            return
        try:
            smtp.quit()
        except Exception:  # noqa: BLE001
            smtp.close()
