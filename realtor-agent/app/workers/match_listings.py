from app.db import get_session_factory, init_db
from app.services.matching.runner import OpportunityMatcher
from app.services.seed import seed_realtor
from app.services.telegram.realtor_agent import RealtorTelegramService


def run() -> dict:
    init_db()
    db = get_session_factory()()
    try:
        realtor = seed_realtor(db)
        created = OpportunityMatcher(db).match_all(realtor)
        telegram = RealtorTelegramService(db)
        for opportunity in created:
            telegram.alert_opportunity(realtor, opportunity)
        db.commit()
        return {"created": [item.public_id for item in created]}
    finally:
        db.close()
