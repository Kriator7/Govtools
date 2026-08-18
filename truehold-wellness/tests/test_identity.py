from pathlib import Path

from thw.identity import REQUIRED_USERNAME, WrongTelegramBotError, assert_wellness_telegram_username


def test_wellness_accepts_thwellness_only():
    assert assert_wellness_telegram_username("THWellness_bot") == REQUIRED_USERNAME
    assert assert_wellness_telegram_username("@THWellness_bot") == REQUIRED_USERNAME


def test_wellness_rejects_deleted_npeppers_bot():
    try:
        assert_wellness_telegram_username("Npeppers_bot")
        raise AssertionError("expected WrongTelegramBotError")
    except WrongTelegramBotError as exc:
        assert "deleted" in str(exc).lower()
        assert "THWellness_bot" in str(exc)


def test_wellness_rejects_realtor_pirateeye_bot():
    try:
        assert_wellness_telegram_username("PirateEye_bot")
        raise AssertionError("expected WrongTelegramBotError")
    except WrongTelegramBotError as exc:
        assert "realtor" in str(exc).lower()
        assert "PirateEye_bot" in str(exc)


def test_source_tree_does_not_import_realtor_agent():
    root = Path(__file__).resolve().parents[1]
    for folder in ("thw", "wellness_agent"):
        for path in (root / folder).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "from app." not in text
            assert "import app" not in text
            assert "realtor-agent/app" not in text
            assert "from app.services" not in text
