"""Year-scoped public ID sequences (TX-2026-000123)."""

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class IdSequence(Base):
    __tablename__ = "id_sequences"
    __table_args__ = (UniqueConstraint("prefix", "year", name="uq_id_sequence_prefix_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prefix: Mapped[str] = mapped_column(String(8))
    year: Mapped[int] = mapped_column(Integer)
    last_value: Mapped[int] = mapped_column(Integer, default=0)
