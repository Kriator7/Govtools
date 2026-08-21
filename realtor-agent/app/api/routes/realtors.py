from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.dependencies import DbSession
from app.models.realtor import Realtor
from app.schemas.realtor import RealtorCreate, RealtorRead, RealtorUpdate
from app.utilities.ids import next_public_id

router = APIRouter(prefix="/realtors", tags=["realtors"])


@router.get("", response_model=list[RealtorRead])
def list_realtors(db: DbSession) -> list[Realtor]:
    return db.query(Realtor).all()


@router.post("", response_model=RealtorRead, status_code=201)
def create_realtor(payload: RealtorCreate, db: DbSession) -> Realtor:
    realtor = Realtor(public_id=next_public_id(db, "RLT"), **payload.model_dump())
    db.add(realtor)
    db.commit()
    db.refresh(realtor)
    return realtor


@router.get("/{realtor_id}", response_model=RealtorRead)
def get_realtor(realtor_id: UUID, db: DbSession) -> Realtor:
    realtor = db.get(Realtor, realtor_id)
    if realtor is None:
        raise HTTPException(status_code=404, detail="Realtor not found")
    return realtor


@router.patch("/{realtor_id}", response_model=RealtorRead)
def update_realtor(realtor_id: UUID, payload: RealtorUpdate, db: DbSession) -> Realtor:
    realtor = db.get(Realtor, realtor_id)
    if realtor is None:
        raise HTTPException(status_code=404, detail="Realtor not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(realtor, key, value)
    db.commit()
    db.refresh(realtor)
    return realtor
