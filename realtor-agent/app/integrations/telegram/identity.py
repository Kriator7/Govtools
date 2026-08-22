"""Realtor Telegram identity lock.

This package talks only to @PirateEye_bot.
"""

REQUIRED_USERNAME = "PirateEye_bot"
FORBIDDEN_USERNAMES = frozenset(
    {
        "THWellness_bot",
        "Mr_North_bot",
        "Npeppers_bot",
        "Npepeers_bot",
        "Npeppert_bot",
    }
)


class WrongTelegramBotError(RuntimeError):
    """Raised when a live token is not @PirateEye_bot."""


def assert_realtor_telegram_username(username: str | None) -> str:
    name = (username or "").lstrip("@").strip()
    if not name:
        raise WrongTelegramBotError(
            "realtor-agent live Telegram token did not return a username. "
            "Expected @PirateEye_bot."
        )
    if name in FORBIDDEN_USERNAMES:
        raise WrongTelegramBotError(
            f"realtor-agent cannot use @{name}. Live Telegram is @PirateEye_bot."
        )
    if name != REQUIRED_USERNAME:
        raise WrongTelegramBotError(
            f"realtor-agent live Telegram must be @{REQUIRED_USERNAME}, got @{name}."
        )
    return name
