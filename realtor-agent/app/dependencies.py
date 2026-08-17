"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.realtor import Realtor


def require_internal_key(
    x_internal_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.environment == "local":
        return
    if not x_internal_key or x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal key")


def get_active_realtor(db: Session = Depends(get_db)) -> Realtor:
    realtor = db.query(Realtor).filter(Realtor.is_active.is_(True)).order_by(Realtor.created_at.asc()).first()
    if realtor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active realtor configured. Run scripts/seed_database.py first.",
        )
    return realtor


DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
ActiveRealtor = Annotated[Realtor, Depends(get_active_realtor)]
