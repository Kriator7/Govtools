from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import ORMModel


class RealtorCreate(ORMModel):
    name: str
    brokerage: str | None = None
    license_number: str | None = None
    license_state: str = "NV"
    phone: str | None = None
    email: EmailStr | None = None
    telegram_user_id: str | None = None
    telegram_chat_id: str | None = None
    timezone: str = "America/Los_Angeles"
    mls_config_ref: str | None = None
    transaction_platform_config_ref: str | None = None
    notification_settings: dict = Field(default_factory=dict)
    is_active: bool = True
    notes: str | None = None


class RealtorUpdate(ORMModel):
    name: str | None = None
    brokerage: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    telegram_chat_id: str | None = None
    is_active: bool | None = None
    notification_settings: dict | None = None
    notes: str | None = None


class RealtorRead(RealtorCreate):
    id: UUID
    public_id: str
