"""Compose mock or live providers from settings."""

from app.config import Settings, get_settings
from app.integrations.email.mock import MockEmailProvider
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
        from app.integrations.telegram.live import LiveTelegramProvider

        return LiveTelegramProvider(settings.telegram_bot_token)
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


def get_email_provider(settings: Settings | None = None) -> MockEmailProvider:
    return MockEmailProvider()


def get_ai_service(settings: Settings | None = None) -> AIService:
    return AIService(MockAIProvider())


def get_signature_provider(settings: Settings | None = None) -> MockSignatureProvider:
    return MockSignatureProvider()
