"""Realtor Telegram identity lock.

This package talks only to @PirateEye_bot. TrueHold Wellness (@Npeppers_bot) is a
different company and a different folder (truehold-wellness/).
"""

REQUIRED_USERNAME = "PirateEye_bot"
FORBIDDEN_USERNAMES = frozenset({"Npeppers_bot", "Npepeers_bot"})


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
            "realtor-agent cannot use the TrueHold Wellness bot. "
            "Use @PirateEye_bot only. Wellness lives in truehold-wellness/ as @Npeppers_bot."
        )
    if name != REQUIRED_USERNAME:
        raise WrongTelegramBotError(
            f"realtor-agent live Telegram must be @{REQUIRED_USERNAME}, got @{name}."
        )
    return name
