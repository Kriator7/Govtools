from app.db import get_session_factory, init_db
from app.models.document import Document
from app.models.enums import DocumentStatus


def run() -> dict:
    init_db()
    db = get_session_factory()()
    try:
        drafts = db.query(Document).filter(Document.status == DocumentStatus.DRAFT.value).count()
        return {"drafts_awaiting_review": drafts}
    finally:
        db.close()
