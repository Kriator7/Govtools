"""TrueHold Wellness Telegram identity lock.

This package talks only to @Npeppers_bot. Realtor acquisition (@PirateEye_bot)
is a different company and lives in realtor-agent/.
"""

REQUIRED_USERNAME = REQUIRED_TELEGRAM_USERNAME = "Npeppers_bot"
FORBIDDEN_USERNAMES = frozenset({"PirateEye_bot"})


class WrongTelegramBotError(RuntimeError):
    """Raised when a live token is not @Npeppers_bot."""


def assert_wellness_telegram_username(username: str | None) -> str:
    name = (username or "").lstrip("@").strip()
    if not name:
        raise WrongTelegramBotError(
            "TrueHold Wellness live Telegram token did not return a username. "
            "Expected @Npeppers_bot."
        )
    if name in FORBIDDEN_USERNAMES:
        raise WrongTelegramBotError(
            "TrueHold Wellness cannot use the realtor bot. "
            "Use @Npeppers_bot only. Realtor acquisition lives in realtor-agent/ as @PirateEye_bot."
        )
    if name != REQUIRED_USERNAME:
        raise WrongTelegramBotError(
            f"TrueHold Wellness live Telegram must be @{REQUIRED_USERNAME}, got @{name}."
        )
    return name
