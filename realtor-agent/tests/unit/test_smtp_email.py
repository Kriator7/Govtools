from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.integrations.email.smtp import SmtpEmailProvider
from app.services.providers import get_email_provider


def test_smtp_sends_via_gmail_settings_and_prefixes_relay(monkeypatch):
    sent: dict = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host
            sent["port"] = port

        def ehlo(self):
            return None

        def starttls(self):
            sent["starttls"] = True

        def login(self, username, password):
            sent["username"] = username
            sent["password"] = password

        def send_message(self, message):
            sent["from"] = message["From"]
            sent["to"] = message["To"]
            sent["subject"] = message["Subject"]
            sent["intended"] = message["X-Intended-Recipient"]
            sent["body"] = message.get_content()

        def noop(self):
            return (250, b"ok")

        def quit(self):
            sent["quit"] = True

        def close(self):
            return None

    monkeypatch.setattr("app.integrations.email.smtp.smtplib.SMTP", FakeSMTP)
    provider = SmtpEmailProvider(
        "smtp.gmail.com",
        587,
        "cardanomint@gmail.com",
        "abcd efgh ijkl mnop",
        starttls=True,
    )
    result = provider.send_email(
        "cardanomint@gmail.com",
        "[realtor-agent test] Property opportunity",
        "Hello investor",
        from_address="cardanomint@gmail.com",
        intended_recipient="investor@example.invalid",
    )
    assert sent["host"] == "smtp.gmail.com"
    assert sent["port"] == 587
    assert sent["starttls"] is True
    assert sent["password"] == "abcdefghijklmnop"
    assert sent["to"] == "cardanomint@gmail.com"
    assert sent["intended"] == "investor@example.invalid"
    assert "Intended recipient: investor@example.invalid" in sent["body"]
    assert result["status"] == "sent"


def test_get_email_provider_requires_app_password(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("EMAIL_SMTP_PASSWORD", "")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValueError, match="EMAIL_SMTP_PASSWORD"):
        get_email_provider(Settings(email_provider="smtp", email_smtp_password=None))
    get_settings.cache_clear()


def test_smtp_health_uses_noop(monkeypatch):
    smtp = MagicMock()
    monkeypatch.setattr("app.integrations.email.smtp.smtplib.SMTP", lambda *args, **kwargs: smtp)
    smtp.ehlo.return_value = None
    smtp.starttls.return_value = None
    smtp.login.return_value = None
    smtp.noop.return_value = (250, b"ok")
    provider = SmtpEmailProvider("smtp.gmail.com", 587, "cardanomint@gmail.com", "secret")
    status, detail = provider.health()
    assert status == "ok"
    smtp.noop.assert_called()
