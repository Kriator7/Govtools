import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUTO_CREATE_TABLES", "true")
os.environ.setdefault("MLS_PROVIDER", "mock")
os.environ.setdefault("TELEGRAM_MODE", "mock")
os.environ.setdefault("SMS_PROVIDER", "mock")
os.environ.setdefault("ENVIRONMENT", "local")

from app.config import get_settings
from app.db import Base, configure_engine, get_session_factory, init_db
from app.main import create_app
from app.services.seed import seed_realtor


@pytest.fixture()
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Session:
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    get_settings.cache_clear()
    configure_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=session.get_bind())


@pytest.fixture()
def realtor(db: Session):
    return seed_realtor(db)


@pytest.fixture()
def client(db: Session, realtor, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from app.db import get_db
    from app.main import create_app

    app = create_app()

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    return TestClient(app)
