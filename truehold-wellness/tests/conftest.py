import os
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

os.environ.setdefault("TELEGRAM_MODE", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")

from thw.config import get_settings
from thw.db import Base, configure_engine, get_session_factory, init_db
from wellness_agent.snapshot import load_current_inbox


@pytest.fixture(autouse=True)
def isolate_wellness_runtime_state(tmp_path, monkeypatch):
    monkeypatch.setenv("WELLNESS_INBOX_STATE_PATH", str(tmp_path / "inbox_state.json"))
    monkeypatch.setenv("WELLNESS_OPERATOR_PATH", str(tmp_path / "operator.json"))
    monkeypatch.setenv("WELLNESS_EMAIL_SEEN_PATH", str(tmp_path / "email_seen.json"))
    load_current_inbox.cache_clear()
    yield
    load_current_inbox.cache_clear()


@pytest.fixture()
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Session:
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'wellness.db'}")
    monkeypatch.setenv("TELEGRAM_MODE", "mock")
    get_settings.cache_clear()
    configure_engine(f"sqlite:///{tmp_path / 'wellness.db'}")
    init_db()
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=session.get_bind())
