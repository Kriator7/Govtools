from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from thw.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_Session = None


def configure_engine(url: str | None = None):
    global _engine, _Session
    settings = get_settings()
    url = url or settings.database_url
    if url.startswith("sqlite"):
        db_path = url.replace("sqlite:///", "", 1)
        if db_path not in {":memory:", ""} and not db_path.startswith("sqlite"):
            path = Path(db_path)
            if not path.is_absolute():
                path = settings.project_root / path
                url = f"sqlite:///{path}"
            path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, future=True, connect_args=connect_args)
    _Session = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


def get_session_factory():
    if _Session is None:
        configure_engine()
    return _Session


def init_db() -> None:
    from thw import models  # noqa: F401

    settings = get_settings()
    if _engine is None:
        configure_engine()
    (settings.project_root / "data" / "exports").mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=_engine)
