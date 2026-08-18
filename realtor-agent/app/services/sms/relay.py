from app.config import Settings, get_settings


def resolve_sms_destination(intended_recipient: str | None, settings: Settings | None = None) -> dict[str, str | None]:
    """To-number for outbound SMS. Relay keeps live Twilio off real investor phones."""
    settings = settings or get_settings()
    intended = (intended_recipient or "").strip() or None
    if settings.sms_relay_mode and settings.sms_relay_to:
        return {
            "to": settings.sms_relay_to.strip(),
            "intended_recipient": intended,
            "relay_mode": "on",
        }
    if settings.sms_relay_mode and settings.sms_provider == "twilio":
        return {
            "to": None,
            "intended_recipient": intended,
            "relay_mode": "blocked",
        }
    return {
        "to": intended,
        "intended_recipient": intended,
        "relay_mode": "on" if settings.sms_relay_mode else "off",
    }
