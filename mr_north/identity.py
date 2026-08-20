"""Mr North Telegram identity lock.

Live Telegram for this package is @Mr_North_bot only.
https://core.telegram.org/bots/api#getme

@THWellness_bot and @PirateEye_bot are different products.
"""

from __future__ import annotations

REQUIRED_USERNAME = "Mr_North_bot"
FORBIDDEN_USERNAMES = frozenset(
    {
        "THWellness_bot",
        "PirateEye_bot",
        "Npeppers_bot",
        "Npepeers_bot",
        "Npeppert_bot",
    }
)


class WrongTelegramBotError(RuntimeError):
    """Raised when a live token is Wellness, realtor, or otherwise not @Mr_North_bot."""


def assert_north_telegram_username(username: str | None) -> str:
    name = (username or "").lstrip("@").strip()
    if not name:
        raise WrongTelegramBotError(
            "Mr North live Telegram expected @Mr_North_bot."
        )
    if name in FORBIDDEN_USERNAMES:
        raise WrongTelegramBotError(
            f"Mr North cannot use @{name}. That bot belongs to Wellness or realtor-agent. "
            "North live Telegram is @Mr_North_bot."
        )
    if name != REQUIRED_USERNAME:
        raise WrongTelegramBotError(
            f"Mr North live Telegram must be @{REQUIRED_USERNAME}, got @{name}."
        )
    return name
