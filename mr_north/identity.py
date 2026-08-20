"""Mr North Telegram identity lock.

North has his own bot. He must not use @THWellness_bot or @PirateEye_bot.
https://core.telegram.org/bots/api#getme
"""

from __future__ import annotations

import os

FORBIDDEN_USERNAMES = frozenset(
    {
        "THWellness_bot",
        "PirateEye_bot",
        "Npeppers_bot",
        "Npepeers_bot",
        "Npeppert_bot",
    }
)
USERNAME_ENV = "NORTH_TELEGRAM_USERNAME"


class WrongTelegramBotError(RuntimeError):
    """Raised when a live token is Wellness, realtor, or otherwise not North."""


def expected_username() -> str:
    return (os.environ.get(USERNAME_ENV) or "").lstrip("@").strip()


def assert_north_telegram_username(username: str | None) -> str:
    name = (username or "").lstrip("@").strip()
    if not name:
        raise WrongTelegramBotError(
            "Mr North live Telegram token did not return a username. "
            "Use North's own bot, not @THWellness_bot or @PirateEye_bot."
        )
    if name in FORBIDDEN_USERNAMES:
        raise WrongTelegramBotError(
            f"Mr North cannot use @{name}. That bot belongs to Wellness or realtor-agent. "
            "Create a separate BotFather bot for North crypto/BLS reports."
        )
    expected = expected_username()
    if expected and name != expected:
        raise WrongTelegramBotError(
            f"Mr North live Telegram must be @{expected}, got @{name}."
        )
    return name
