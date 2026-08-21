from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.dependencies import ActiveRealtor, DbSession
from app.models.investor import Investor
from app.models.investor_criteria import DEFAULT_STRICT_FIELDS, InvestorCriteria
from app.schemas.investor import (
    CriteriaCreate,
    CriteriaRead,
    InvestorCreate,
    InvestorImportResult,
    InvestorRead,
    InvestorUpdate,
)
from app.services.importing import InvestorImportService
from app.utilities.ids import next_public_id

router = APIRouter(prefix="/investors", tags=["investors"])


@router.get("", response_model=list[InvestorRead])
def list_investors(db: DbSession, realtor: ActiveRealtor) -> list[Investor]:
    return db.query(Investor).filter(Investor.realtor_id == realtor.id).all()


@router.post("", response_model=InvestorRead, status_code=201)
def create_investor(payload: InvestorCreate, db: DbSession, realtor: ActiveRealtor) -> Investor:
    investor = Investor(
        public_id=next_public_id(db, "INV"),
        realtor_id=realtor.id,
        **payload.model_dump(),
    )
    db.add(investor)
    db.commit()
    db.refresh(investor)
    return investor


@router.get("/{investor_id}", response_model=InvestorRead)
def get_investor(investor_id: UUID, db: DbSession, realtor: ActiveRealtor) -> Investor:
    investor = _get(db, realtor, investor_id)
    return investor


@router.patch("/{investor_id}", response_model=InvestorRead)
def update_investor(investor_id: UUID, payload: InvestorUpdate, db: DbSession, realtor: ActiveRealtor) -> Investor:
    investor = _get(db, realtor, investor_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(investor, key, value)
    db.commit()
    db.refresh(investor)
    return investor


@router.get("/{investor_id}/criteria", response_model=list[CriteriaRead])
def list_criteria(investor_id: UUID, db: DbSession, realtor: ActiveRealtor) -> list[InvestorCriteria]:
    _get(db, realtor, investor_id)
    return (
        db.query(InvestorCriteria)
        .filter(InvestorCriteria.investor_id == investor_id, InvestorCriteria.realtor_id == realtor.id)
        .all()
    )


@router.post("/{investor_id}/criteria", response_model=CriteriaRead, status_code=201)
def create_criteria(
    investor_id: UUID, payload: CriteriaCreate, db: DbSession, realtor: ActiveRealtor
) -> InvestorCriteria:
    _get(db, realtor, investor_id)
    data = payload.model_dump()
    if not data.get("strict_fields"):
        data["strict_fields"] = list(DEFAULT_STRICT_FIELDS)
    criteria = InvestorCriteria(
        public_id=next_public_id(db, "CRT"),
        realtor_id=realtor.id,
        investor_id=investor_id,
        **data,
    )
    db.add(criteria)
    db.commit()
    db.refresh(criteria)
    return criteria


@router.post("/import", response_model=InvestorImportResult)
async def import_investors(
    db: DbSession,
    realtor: ActiveRealtor,
    file: UploadFile = File(...),
) -> dict:
    data = await file.read()
    result = InvestorImportService(db).import_bytes(realtor, data, file.filename or "upload.csv")
    db.commit()
    return result


def _get(db, realtor, investor_id: UUID) -> Investor:
    investor = (
        db.query(Investor)
        .filter(Investor.id == investor_id, Investor.realtor_id == realtor.id)
        .one_or_none()
    )
    if investor is None:
        raise HTTPException(status_code=404, detail="Investor not found")
    return investor
