from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.db import get_session_factory
from app.schemas.common import HealthComponent, HealthResponse
from app.services.providers import get_email_provider, get_mls_provider, get_sms_provider, get_telegram_provider
from app.integrations.open_leads.catalog import providers_for

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
        checked_at=datetime.now(timezone.utc),
        components=[HealthComponent(name="api", status="ok")],
    )


@router.get("/health/database", response_model=HealthResponse)
def health_database() -> HealthResponse:
    settings = get_settings()
    try:
        db = get_session_factory()()
        db.execute(text("SELECT 1"))
        db.close()
        status, detail = "ok", "query succeeded"
    except Exception as exc:  # noqa: BLE001
        status, detail = "error", str(exc)
    return HealthResponse(
        status=status,
        service=settings.app_name,
        environment=settings.environment,
        checked_at=datetime.now(timezone.utc),
        components=[HealthComponent(name="database", status=status, detail=detail)],
    )


@router.get("/health/mls", response_model=HealthResponse)
def health_mls() -> HealthResponse:
    return _provider_health("mls", get_mls_provider().health())


@router.get("/health/telegram", response_model=HealthResponse)
def health_telegram() -> HealthResponse:
    return _provider_health("telegram", get_telegram_provider().health())


@router.get("/health/twilio", response_model=HealthResponse)
def health_twilio() -> HealthResponse:
    return _provider_health("twilio", get_sms_provider().health())


@router.get("/health/email", response_model=HealthResponse)
def health_email() -> HealthResponse:
    try:
        return _provider_health("email", get_email_provider().health())
    except Exception as exc:  # noqa: BLE001
        return _provider_health("email", ("error", str(exc)))


@router.get("/health/open-leads", response_model=HealthResponse)
def health_open_leads() -> HealthResponse:
    settings = get_settings()
    try:
        rows = providers_for(mode=settings.open_leads_mode)
        detail = f"mode={settings.open_leads_mode} providers={len(rows)}"
        return _provider_health("open-leads", ("ok", detail))
    except Exception as exc:  # noqa: BLE001
        return _provider_health("open-leads", ("error", str(exc)))


def _provider_health(name: str, result: tuple[str, str]) -> HealthResponse:
    settings = get_settings()
    status, detail = result
    return HealthResponse(
        status=status,
        service=settings.app_name,
        environment=settings.environment,
        checked_at=datetime.now(timezone.utc),
        components=[HealthComponent(name=name, status=status, detail=detail)],
    )
