"""TrueHold Wellness Telegram identity lock. @Npeppers_bot only."""

REQUIRED_USERNAME = "Npeppers_bot"
FORBIDDEN_USERNAMES = frozenset({"PirateEye_bot"})


class WrongTelegramBotError(RuntimeError):
    """Raised when a live token is not @Npeppers_bot."""


def assert_wellness_telegram_username(username: str | None) -> str:
    name = (username or "").lstrip("@").strip()
    if not name:
        raise WrongTelegramBotError("TrueHold Wellness live Telegram expected @Npeppers_bot.")
    if name in FORBIDDEN_USERNAMES:
        raise WrongTelegramBotError(
            "TrueHold Wellness cannot use @PirateEye_bot. That bot is realtor-agent only."
        )
    if name != REQUIRED_USERNAME:
        raise WrongTelegramBotError(
            f"TrueHold Wellness live Telegram must be @{REQUIRED_USERNAME}, got @{name}."
        )
    return name
