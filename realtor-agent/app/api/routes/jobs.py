from fastapi import APIRouter, Depends

from app.dependencies import ActiveRealtor, DbSession, require_internal_key
from app.services.matching.runner import OpportunityMatcher
from app.services.mls.ingest import ListingIngestService
from app.services.providers import get_mls_provider
from app.services.telegram.realtor_agent import RealtorTelegramService

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_internal_key)])


@router.post("/ingest-listings")
def job_ingest(db: DbSession, realtor: ActiveRealtor) -> dict:
    result = ListingIngestService(db, get_mls_provider()).sync(realtor, incremental=True)
    db.commit()
    return result


@router.post("/match-listings")
def job_match(db: DbSession, realtor: ActiveRealtor) -> dict:
    created = OpportunityMatcher(db).match_all(realtor)
    telegram = RealtorTelegramService(db)
    for opportunity in created:
        telegram.alert_opportunity(realtor, opportunity)
    db.commit()
    return {"created": len(created), "ids": [item.public_id for item in created]}
