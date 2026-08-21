"""Settings for TrueHold Wellness. Independent env file; never read realtor-agent/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PACKAGE_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "truehold-wellness"
    environment: str = "local"
    database_url: str = "sqlite:///./data/wellness.db"
    auto_create_tables: bool = True

    telegram_mode: str = "mock"
    telegram_bot_token: str | None = None
    telegram_operator_chat_id: str | None = None

    email_provider: str = "mock"
    email_from: str = ""
    email_inbox_path: str = "./data/imports/sample_order_emails.json"

    @property
    def project_root(self) -> Path:
        return PACKAGE_ROOT

    @property
    def inbox_path(self) -> Path:
        path = Path(self.email_inbox_path)
        if not path.is_absolute():
            path = PACKAGE_ROOT / path
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
