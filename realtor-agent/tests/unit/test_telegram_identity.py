from app.integrations.telegram.identity import (
    REQUIRED_USERNAME,
    WrongTelegramBotError,
    assert_realtor_telegram_username,
)


def test_realtor_accepts_pirateeye_only():
    assert assert_realtor_telegram_username("PirateEye_bot") == REQUIRED_USERNAME
    assert assert_realtor_telegram_username("@PirateEye_bot") == REQUIRED_USERNAME


def test_realtor_rejects_wellness_thwellness_bot():
    try:
        assert_realtor_telegram_username("THWellness_bot")
        raise AssertionError("expected WrongTelegramBotError")
    except WrongTelegramBotError as exc:
        assert "THWellness_bot" in str(exc)
        assert "PirateEye_bot" in str(exc)


def test_realtor_rejects_deleted_npeppers_bot():
    try:
        assert_realtor_telegram_username("Npeppers_bot")
        raise AssertionError("expected WrongTelegramBotError")
    except WrongTelegramBotError as exc:
        assert "Npeppers_bot" in str(exc)
        assert "PirateEye_bot" in str(exc)


def test_realtor_rejects_other_usernames():
    try:
        assert_realtor_telegram_username("SomeOther_bot")
        raise AssertionError("expected WrongTelegramBotError")
    except WrongTelegramBotError as exc:
        assert "PirateEye_bot" in str(exc)


def test_realtor_rejects_mr_north_bot():
    try:
        assert_realtor_telegram_username("Mr_North_bot")
        raise AssertionError("expected WrongTelegramBotError")
    except WrongTelegramBotError as exc:
        assert "Mr_North_bot" in str(exc)
        assert "PirateEye_bot" in str(exc)
