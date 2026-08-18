import os
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

os.environ.setdefault("TELEGRAM_MODE", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")

from thw.config import get_settings
from thw.db import Base, configure_engine, get_session_factory, init_db


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
