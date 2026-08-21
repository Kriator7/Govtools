"""Realtor Telegram identity lock.

This package talks only to @PirateEye_bot. TrueHold Wellness (@THWellness_bot) and
Mr North (@Mr_North_bot) are different products.
"""

REQUIRED_USERNAME = "PirateEye_bot"
WELLNESS_USERNAMES = frozenset(
    {"THWellness_bot", "Npeppers_bot", "Npepeers_bot", "Npeppert_bot"}
)
NORTH_USERNAME = "Mr_North_bot"
FORBIDDEN_USERNAMES = WELLNESS_USERNAMES | {NORTH_USERNAME}


class WrongTelegramBotError(RuntimeError):
    """Raised when a live token is not @PirateEye_bot."""


def assert_realtor_telegram_username(username: str | None) -> str:
    name = (username or "").lstrip("@").strip()
    if not name:
        raise WrongTelegramBotError(
            "realtor-agent live Telegram token did not return a username. "
            "Expected @PirateEye_bot."
        )
    if name in WELLNESS_USERNAMES:
        raise WrongTelegramBotError(
            "realtor-agent cannot use the TrueHold Wellness bot. "
            "Use @PirateEye_bot only. Wellness lives in truehold-wellness/ as @THWellness_bot."
        )
    if name == NORTH_USERNAME:
        raise WrongTelegramBotError(
            "realtor-agent cannot use @Mr_North_bot. That bot is TrueHold crypto/macro. "
            "Realtor live Telegram is @PirateEye_bot."
        )
    if name != REQUIRED_USERNAME:
        raise WrongTelegramBotError(
            f"realtor-agent live Telegram must be @{REQUIRED_USERNAME}, got @{name}."
        )
    return name
