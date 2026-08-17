"""SQLAlchemy engine and session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def _engine_kwargs(database_url: str) -> dict:
    kwargs: dict = {"future": True, "pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return kwargs


def configure_engine(database_url: str | None = None) -> Engine:
    global engine, SessionLocal
    url = database_url or get_settings().database_url
    engine = create_engine(url, **_engine_kwargs(url))
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    return engine


def get_engine() -> Engine:
    if engine is None:
        configure_engine()
    assert engine is not None
    return engine


def get_session_factory() -> sessionmaker[Session]:
    if SessionLocal is None:
        configure_engine()
    assert SessionLocal is not None
    return SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables in local/demo mode. Production should use Alembic."""
    from app import models  # noqa: F401

    settings = get_settings()
    if settings.auto_create_tables:
        settings.storage_path.mkdir(parents=True, exist_ok=True)
        (settings.project_root / "data").mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(bind=get_engine())
