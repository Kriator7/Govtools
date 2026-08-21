"""Email channel. Default test relay is EMAIL_FROM / EMAIL_RELAY_TO (cardanomint@gmail.com)."""

from app.services.email.relay import resolve_email_envelope

__all__ = ["resolve_email_envelope"]
