"""Five-field cron matcher. Evaluated in America/Los_Angeles."""

from __future__ import annotations

from datetime import datetime, timedelta

from jarvis.clock import TZ, ensure


def _parts(expr: str) -> list[str]:
    fields = expr.split()
    if len(fields) != 5:
        raise ValueError("cron must be five fields: minute hour day month weekday")
    return fields


def _match_field(token: str, value: int, low: int, high: int) -> bool:
    for piece in token.split(","):
        if piece == "*":
            return True
        if piece.startswith("*/"):
            step = int(piece[2:])
            if step <= 0:
                raise ValueError("cron step must be positive")
            if value % step == 0:
                return True
            continue
        if "-" in piece:
            start_s, end_s = piece.split("-", 1)
            start, end = int(start_s), int(end_s)
            if start <= value <= end:
                return True
            continue
        number = int(piece)
        if number == value or (low == 0 and high == 7 and number == 7 and value == 0):
            return True
    return False


def matches(expr: str, moment: datetime) -> bool:
    minute, hour, day, month, weekday = _parts(expr)
    local = ensure(moment)
    dow = (local.weekday() + 1) % 7  # Monday=0 in datetime; cron Sunday=0
    day_ok = _match_field(day, local.day, 1, 31)
    dow_ok = _match_field(weekday, dow, 0, 7)
    if day != "*" and weekday != "*":
        calendar_ok = day_ok or dow_ok
    else:
        calendar_ok = day_ok and dow_ok
    return (
        _match_field(minute, local.minute, 0, 59)
        and _match_field(hour, local.hour, 0, 23)
        and _match_field(month, local.month, 1, 12)
        and calendar_ok
    )


def next_after(expr: str, moment: datetime) -> datetime:
    _parts(expr)
    cursor = ensure(moment).replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(366 * 24 * 60):
        if matches(expr, cursor):
            return cursor
        cursor += timedelta(minutes=1)
    raise ValueError("cron did not match within a year")


def validate_expr(expr: str, moment: datetime | None = None) -> datetime:
    from jarvis.clock import now

    return next_after(expr, moment or now())
