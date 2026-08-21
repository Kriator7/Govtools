from app.config import Settings, get_settings


def resolve_email_envelope(intended_recipient: str, settings: Settings | None = None) -> dict[str, str | None]:
    """From/to for outbound mail. Relay address is env-configurable."""
    settings = settings or get_settings()
    if settings.email_relay_mode:
        return {
            "from_address": settings.email_from,
            "to": settings.email_relay_to,
            "intended_recipient": intended_recipient,
            "relay_mode": "on",
        }
    return {
        "from_address": settings.email_from,
        "to": intended_recipient,
        "intended_recipient": intended_recipient,
        "relay_mode": "off",
    }
