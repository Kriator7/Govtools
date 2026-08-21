"""Compose mock or live providers from settings."""

from app.config import Settings, get_settings
from app.integrations.email.base import EmailProvider
from app.integrations.email.mock import MockEmailProvider
from app.integrations.email.smtp import SmtpEmailProvider
from app.integrations.esign.mock import MockSignatureProvider
from app.integrations.mls.base import MLSProvider
from app.integrations.mls.mock import MockMLSProvider
from app.integrations.telegram.base import TelegramProvider
from app.integrations.telegram.mock import MockTelegramProvider
from app.integrations.twilio.base import SMSProvider
from app.integrations.twilio.mock import MockSMSProvider
from app.services.ai.mock import MockAIProvider
from app.services.ai.service import AIService


def get_mls_provider(settings: Settings | None = None) -> MLSProvider:
    settings = settings or get_settings()
    return MockMLSProvider()


def get_telegram_provider(settings: Settings | None = None) -> TelegramProvider:
    settings = settings or get_settings()
    if settings.telegram_mode == "live" and settings.telegram_bot_token:
        from app.integrations.telegram.identity import assert_realtor_telegram_username
        from app.integrations.telegram.live import LiveTelegramProvider

        provider = LiveTelegramProvider(settings.telegram_bot_token)
        assert_realtor_telegram_username(provider.get_username())
        return provider
    return MockTelegramProvider()


def get_sms_provider(settings: Settings | None = None) -> SMSProvider:
    settings = settings or get_settings()
    if (
        settings.sms_provider == "twilio"
        and settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
    ):
        from app.integrations.twilio.live import LiveSMSProvider

        return LiveSMSProvider(
            settings.twilio_account_sid,
            settings.twilio_auth_token,
            settings.twilio_from_number,
        )
    return MockSMSProvider()


def get_email_provider(settings: Settings | None = None) -> EmailProvider:
    settings = settings or get_settings()
    if settings.email_provider in {"smtp", "gmail"}:
        username = settings.email_smtp_username or settings.email_from
        password = settings.email_smtp_password
        if not password:
            raise ValueError(
                "EMAIL_SMTP_PASSWORD is required when EMAIL_PROVIDER=smtp. "
                "Create a Gmail App Password: https://support.google.com/accounts/answer/185833"
            )
        return SmtpEmailProvider(
            host=settings.email_smtp_host,
            port=settings.email_smtp_port,
            username=username,
            password=password,
            starttls=settings.email_smtp_starttls,
        )
    return MockEmailProvider()


def get_ai_service(settings: Settings | None = None) -> AIService:
    return AIService(MockAIProvider())


def get_signature_provider(settings: Settings | None = None) -> MockSignatureProvider:
    return MockSignatureProvider()
