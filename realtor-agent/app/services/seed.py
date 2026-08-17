from sqlalchemy.orm import Session

from app.models.realtor import Realtor
from app.utilities.ids import next_public_id


def seed_realtor(db: Session) -> Realtor:
    existing = db.query(Realtor).filter(Realtor.is_active.is_(True)).order_by(Realtor.created_at.asc()).first()
    if existing:
        return existing
    realtor = Realtor(
        public_id=next_public_id(db, "RLT"),
        name="Nevada Demo Realtor",
        brokerage="Independent / Demo Brokerage",
        license_number="NV-DEMO-0001",
        license_state="NV",
        phone="+17025550100",
        email="realtor@example.invalid",
        telegram_chat_id="mock-realtor",
        timezone="America/Los_Angeles",
        mls_config_ref="secret:mls-demo-config",
        transaction_platform_config_ref="secret:transaction-platform-demo",
        notification_settings={"telegram": True, "critical_failures": True},
        is_active=True,
        notes="Local demonstration realtor. Replace before production.",
    )
    db.add(realtor)
    db.flush()
    return realtor
