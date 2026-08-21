"""Public ID generation. Example: TX-2026-000123."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.id_sequence import IdSequence


def next_public_id(db: Session, prefix: str, width: int = 6) -> str:
    year = datetime.now(timezone.utc).year
    seq = (
        db.query(IdSequence)
        .filter(IdSequence.prefix == prefix, IdSequence.year == year)
        .one_or_none()
    )
    if seq is None:
        seq = IdSequence(prefix=prefix, year=year, last_value=0)
        db.add(seq)
        db.flush()
    seq.last_value += 1
    db.flush()
    return f"{prefix}-{year}-{seq.last_value:0{width}d}"
