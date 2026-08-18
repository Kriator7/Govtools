from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.dependencies import ActiveRealtor, DbSession
from app.models.listing import Listing
from app.schemas.listing import ListingCreate, ListingRead
from app.services.matching.duplicates import listing_fingerprint
from app.services.matching.runner import OpportunityMatcher
from app.services.mls.ingest import ListingIngestService
from app.services.providers import get_mls_provider
from app.services.telegram.realtor_agent import RealtorTelegramService
from app.utilities.ids import next_public_id

router = APIRouter(prefix="/listings", tags=["listings"])


class ListingArvUpdate(BaseModel):
    arv: Decimal

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=list[ListingRead])
def list_listings(db: DbSession, realtor: ActiveRealtor) -> list[Listing]:
    return db.query(Listing).filter(Listing.realtor_id == realtor.id).all()


@router.post("", response_model=ListingRead, status_code=201)
def create_listing(payload: ListingCreate, db: DbSession, realtor: ActiveRealtor) -> Listing:
    listing = Listing(
        public_id=next_public_id(db, "LST"),
        realtor_id=realtor.id,
        **payload.model_dump(),
    )
    listing.material_fingerprint = listing_fingerprint(listing)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.get("/{listing_id}", response_model=ListingRead)
def get_listing(listing_id: UUID, db: DbSession, realtor: ActiveRealtor) -> Listing:
    listing = (
        db.query(Listing).filter(Listing.id == listing_id, Listing.realtor_id == realtor.id).one_or_none()
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.post("/ingest")
def ingest_listings(db: DbSession, realtor: ActiveRealtor) -> dict:
    result = ListingIngestService(db, get_mls_provider()).sync(realtor)
    db.commit()
    return result


@router.post("/{listing_id}/arv")
def set_listing_arv(
    listing_id: UUID, payload: ListingArvUpdate, db: DbSession, realtor: ActiveRealtor
) -> dict:
    listing = (
        db.query(Listing).filter(Listing.id == listing_id, Listing.realtor_id == realtor.id).one_or_none()
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.arv = payload.arv
    listing.material_fingerprint = listing_fingerprint(listing)
    created = OpportunityMatcher(db).match_listing(realtor, listing)
    telegram = RealtorTelegramService(db)
    for opportunity in created:
        telegram.alert_opportunity(realtor, opportunity)
    db.commit()
    return {
        "listing_id": str(listing.id),
        "arv": str(listing.arv),
        "opportunities": [item.public_id for item in created],
        "review_notice": "ARV was entered by a human. The system does not invent ARV.",
    }
