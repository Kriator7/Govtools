from app.db import get_session_factory, init_db
from app.models.communication import Communication
from app.models.enums import DeliveryStatus


def run() -> dict:
    init_db()
    db = get_session_factory()()
    try:
        failed = (
            db.query(Communication)
            .filter(Communication.status == DeliveryStatus.FAILED.value)
            .count()
        )
        return {"failed_notifications": failed, "retried": 0}
    finally:
        db.close()
