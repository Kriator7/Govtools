from thw.config import Settings, get_settings
from thw.identity import assert_wellness_telegram_username
from thw.telegram import WellnessTelegram
from thw.telegram_mock import MockWellnessTelegram


def get_telegram(settings: Settings | None = None):
    settings = settings or get_settings()
    if settings.telegram_mode == "live" and settings.telegram_bot_token:
        client = WellnessTelegram(settings.telegram_bot_token)
        assert_wellness_telegram_username(client.get_username())
        return client
    return MockWellnessTelegram()
