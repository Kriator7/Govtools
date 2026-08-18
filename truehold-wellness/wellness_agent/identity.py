"""TrueHold Wellness Telegram identity lock. @THWellness_bot only.

@Npeppers_bot was deleted in BotFather. Telegram /deletebot cannot be undone
(https://core.telegram.org/bots/features). Live Telegram for this package is
the replacement bot @THWellness_bot. Realtor acquisition (@PirateEye_bot)
lives in realtor-agent/.
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
            "TrueHold Wellness live Telegram expected @THWellness_bot."
        )
    if name in FORBIDDEN_USERNAMES:
        raise WrongTelegramBotError(
            "TrueHold Wellness cannot use @PirateEye_bot. That bot is realtor-agent only."
        )
    if name in PREDECESSOR_USERNAMES:
        raise WrongTelegramBotError(
            f"@{name} was deleted and cannot be restored. "
            "TrueHold Wellness live Telegram is @THWellness_bot."
        )
    if name != REQUIRED_USERNAME:
        raise WrongTelegramBotError(
            f"TrueHold Wellness live Telegram must be @{REQUIRED_USERNAME}, got @{name}."
        )
    return name
