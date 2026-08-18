"""Application settings.

Credentials are never stored in the database. Local development reads environment
variables. Production should set SECRET_BACKEND=gcp and store secrets in
Google Secret Manager: https://cloud.google.com/secret-manager/docs
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "realtor-agent"
    environment: str = "local"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    internal_api_key: str = "change-me-local-only"

    database_url: str = "sqlite:///./data/realtor_agent.db"
    auto_create_tables: bool = True
    redis_url: str = "redis://localhost:6379/0"

    secret_backend: str = "env"

    mls_provider: str = "mock"
    telegram_mode: str = "mock"
    sms_provider: str = "mock"
    email_provider: str = "mock"
    ai_provider: str = "mock"
    esign_provider: str = "mock"
    storage_backend: str = "local"
    local_storage_path: str = "./data/storage"

    alert_min_score: int = 70
    alert_below_threshold: bool = False

    default_timezone: str = "America/Los_Angeles"
    default_license_state: str = "NV"

    # Testing relay. Change these without code edits when Damian goes live.
    email_from: str = "cardanomint@gmail.com"
    email_relay_to: str = "cardanomint@gmail.com"
    email_relay_mode: bool = True
    email_subject_prefix: str = "[realtor-agent test]"
    email_smtp_host: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_smtp_username: str | None = None
    email_smtp_password: str | None = None
    email_smtp_starttls: bool = True

    # Damian's live preference is SMS. Relay keeps test texts off real investors.
    sms_relay_mode: bool = True
    sms_relay_to: str | None = None
    notify_email_copy: bool = True

    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_operator_chat_id: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    mls_api_base_url: str | None = None
    mls_api_key_secret_name: str | None = None
    ai_api_key: str | None = None
    esign_api_key: str | None = None
    gcs_bucket: str | None = None
    gcp_project_id: str | None = None

    scoring_weights_path: str = "mappings/scoring_weights.json"
    templates_path: str = "templates"
    mappings_path: str = "mappings"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def storage_path(self) -> Path:
        path = Path(self.local_storage_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()


def scoring_weights_defaults() -> dict[str, float]:
    """Default opportunity scoring deductions for preferred-field misses."""
    return {
        "min_price": 8,
        "max_price": 15,
        "zip_codes": 12,
        "cities": 10,
        "neighborhoods": 6,
        "property_types": 12,
        "min_bedrooms": 10,
        "min_bathrooms": 8,
        "min_sqft": 6,
        "max_sqft": 3,
        "min_lot_sqft": 4,
        "year_built_min": 5,
        "year_built_max": 3,
        "max_hoa": 6,
        "max_dom": 4,
        "min_cap_rate": 8,
        "min_estimated_rent": 8,
        "max_grm": 5,
        "max_repair_estimate": 7,
        "min_cash_flow": 8,
        "min_desired_equity": 6,
        "min_desired_discount": 6,
        "occupancy_status": 3,
        "seller_financing": 4,
        "foreclosure": 3,
        "short_sale": 3,
        "assumable_loan": 3,
        "price_reduction": 3,
        "hoa_required": 4,
        "max_price_pct_of_arv": 15,
    }
