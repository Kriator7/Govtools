"""TrueHold Wellness Telegram identity lock.

This package talks only to @THWellness_bot, the BotFather replacement for the
deleted @Npeppers_bot (https://core.telegram.org/bots/features — /deletebot
cannot be undone). Realtor acquisition (@PirateEye_bot) is a different company
and lives in realtor-agent/.
"""

REQUIRED_USERNAME = REQUIRED_TELEGRAM_USERNAME = "THWellness_bot"
FORBIDDEN_USERNAMES = frozenset({"PirateEye_bot"})
PREDECESSOR_USERNAMES = frozenset({"Npeppers_bot", "Npepeers_bot", "Npeppert_bot"})


class WrongTelegramBotError(RuntimeError):
    """Raised when a live token is not @THWellness_bot."""


def assert_wellness_telegram_username(username: str | None) -> str:
    name = (username or "").lstrip("@").strip()
    if not name:
        raise WrongTelegramBotError(
            "TrueHold Wellness live Telegram token did not return a username. "
            "Expected @THWellness_bot."
        )
    if name in FORBIDDEN_USERNAMES:
        raise WrongTelegramBotError(
            "TrueHold Wellness cannot use the realtor bot. "
            "Use @THWellness_bot only. Realtor acquisition lives in realtor-agent/ as @PirateEye_bot."
        )
    if name in PREDECESSOR_USERNAMES:
        raise WrongTelegramBotError(
            f"@{name} was deleted and cannot be restored. "
            "Use @THWellness_bot only. Realtor acquisition lives in realtor-agent/ as @PirateEye_bot."
        )
    if name != REQUIRED_USERNAME:
        raise WrongTelegramBotError(
            f"TrueHold Wellness live Telegram must be @{REQUIRED_USERNAME}, got @{name}."
        )
    return name
