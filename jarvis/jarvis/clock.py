"""Operational clock. America/Los_Angeles is the only business timezone."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TZ_NAME = "America/Los_Angeles"
TZ = ZoneInfo(TZ_NAME)


def now() -> datetime:
    return datetime.now(TZ)


def ensure(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=TZ)
    return moment.astimezone(TZ)


def iso(moment: datetime | None = None) -> str:
    current = ensure(moment or now())
    return current.isoformat(timespec="seconds")
