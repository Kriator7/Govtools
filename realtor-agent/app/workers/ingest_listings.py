from app.db import get_session_factory, init_db
from app.services.mls.ingest import ListingIngestService
from app.services.providers import get_mls_provider
from app.services.seed import seed_realtor


def run() -> dict:
    init_db()
    db = get_session_factory()()
    try:
        realtor = seed_realtor(db)
        result = ListingIngestService(db, get_mls_provider()).sync(realtor, incremental=True)
        db.commit()
        return result
    finally:
        db.close()
