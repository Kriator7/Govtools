"""Official Bureau of Labor Statistics prints for Mr North hourly reports.

API v1 (no key): https://www.bls.gov/developers/api_signature.htm
POST https://api.bls.gov/publicAPI/v1/timeseries/data/
Series catalog: https://www.bls.gov/help/hlpforma.htm

One POST per hour stays under the v1 cap of 25 queries/day.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

BLS_TIMESERIES_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
USER_AGENT = "mr-north/0.1 (TrueHold crypto hourly; https://www.bls.gov/developers/)"

# Popular official series used on the BLS public dashboard.
SERIES = (
    {
        "id": "LNS14000000",
        "label": "Unemployment rate (SA)",
        "unit": "percent",
        "survey": "CPS",
    },
    {
        "id": "CES0000000001",
        "label": "Total nonfarm payrolls (SA)",
        "unit": "thousands",
        "survey": "CES",
    },
    {
        "id": "CES0500000003",
        "label": "Average hourly earnings, total private (SA)",
        "unit": "dollars",
        "survey": "CES",
    },
    {
        "id": "CUUR0000SA0",
        "label": "CPI-U all items (not SA)",
        "unit": "index",
        "survey": "CPI",
    },
    {
        "id": "CUUR0000SA0L1E",
        "label": "CPI-U all items less food and energy (not SA)",
        "unit": "index",
        "survey": "CPI",
    },
)


@dataclass(frozen=True)
class SeriesPrint:
    series_id: str
    label: str
    unit: str
    year: str
    period: str
    period_name: str
    value: float
    previous_value: float | None
    yoy_value: float | None

    def month_change(self) -> float | None:
        if self.previous_value is None:
            return None
        return self.value - self.previous_value

    def month_change_pct(self) -> float | None:
        if self.previous_value in (None, 0):
            return None
        return (self.value / self.previous_value - 1.0) * 100.0

    def yoy_change_pct(self) -> float | None:
        if self.yoy_value in (None, 0):
            return None
        return (self.value / self.yoy_value - 1.0) * 100.0


@dataclass(frozen=True)
class BlsSnapshot:
    fetched_at: datetime
    prints: tuple[SeriesPrint, ...]
    fingerprint: str
    source: str = BLS_TIMESERIES_URL


def _float(raw: str) -> float:
    return float(str(raw).replace(",", ""))


def _latest_two_and_yoy(points: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    ordered = sorted(
        points,
        key=lambda row: (str(row.get("year") or ""), str(row.get("period") or "")),
        reverse=True,
    )
    latest = ordered[0]
    previous = ordered[1] if len(ordered) > 1 else None
    yoy = None
    latest_year = int(latest.get("year") or 0)
    latest_period = str(latest.get("period") or "")
    for row in ordered:
        if int(row.get("year") or 0) == latest_year - 1 and str(row.get("period") or "") == latest_period:
            yoy = row
            break
    return latest, previous, yoy


def fetch_snapshot(
    *,
    opener: Callable[..., Any] | None = None,
    timeout: int = 30,
    start_year: int | None = None,
    end_year: int | None = None,
) -> BlsSnapshot:
    """Pull the latest official prints. https://www.bls.gov/developers/api_signature.htm"""
    now = datetime.now(timezone.utc)
    end = end_year or now.year
    start = start_year or (end - 1)
    body = json.dumps(
        {
            "seriesid": [item["id"] for item in SERIES],
            "startyear": str(start),
            "endyear": str(end),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        BLS_TIMESERIES_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    post = opener or urllib.request.urlopen
    try:
        with post(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"BLS API request failed: {exc}") from exc
    if payload.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(payload.get("message") or "BLS API request was not successful")
    by_id = {
        str(row.get("seriesID") or ""): row
        for row in ((payload.get("Results") or {}).get("series") or [])
    }
    prints: list[SeriesPrint] = []
    fingerprint_parts: list[str] = []
    for meta in SERIES:
        row = by_id.get(meta["id"])
        points = list((row or {}).get("data") or [])
        if not points:
            continue
        latest, previous, yoy = _latest_two_and_yoy(points)
        print_ = SeriesPrint(
            series_id=meta["id"],
            label=meta["label"],
            unit=meta["unit"],
            year=str(latest.get("year") or ""),
            period=str(latest.get("period") or ""),
            period_name=str(latest.get("periodName") or latest.get("period") or ""),
            value=_float(str(latest.get("value"))),
            previous_value=_float(str(previous.get("value"))) if previous else None,
            yoy_value=_float(str(yoy.get("value"))) if yoy else None,
        )
        prints.append(print_)
        fingerprint_parts.append(
            f"{print_.series_id}:{print_.year}{print_.period}:{print_.value}"
        )
    if not prints:
        raise RuntimeError("BLS API returned no series prints")
    return BlsSnapshot(
        fetched_at=now,
        prints=tuple(prints),
        fingerprint="|".join(fingerprint_parts),
    )


def _format_value(print_: SeriesPrint) -> str:
    if print_.unit == "percent":
        return f"{print_.value:.1f}%"
    if print_.unit == "dollars":
        return f"${print_.value:.2f}"
    if print_.unit == "thousands":
        return f"{print_.value:,.0f}k"
    return f"{print_.value:,.3f}"


def _format_delta(print_: SeriesPrint) -> str:
    bits: list[str] = []
    if print_.unit == "percent" and print_.month_change() is not None:
        change = print_.month_change()
        sign = "+" if change > 0 else ""
        bits.append(f"m/m {sign}{change:.1f} pp")
    elif print_.unit == "thousands" and print_.month_change() is not None:
        jobs = print_.month_change() * 1000
        sign = "+" if jobs > 0 else ""
        bits.append(f"m/m {sign}{jobs:,.0f}")
    elif print_.month_change_pct() is not None:
        change = print_.month_change_pct()
        sign = "+" if change > 0 else ""
        bits.append(f"m/m {sign}{change:.2f}%")
    if print_.unit == "percent" and print_.yoy_value is not None:
        change = print_.value - print_.yoy_value
        sign = "+" if change > 0 else ""
        bits.append(f"y/y {sign}{change:.1f} pp")
    elif print_.yoy_change_pct() is not None:
        change = print_.yoy_change_pct()
        sign = "+" if change > 0 else ""
        bits.append(f"y/y {sign}{change:.2f}%")
    return f" ({'; '.join(bits)})" if bits else ""


def format_breakdown(snapshot: BlsSnapshot, *, unchanged: bool = False) -> str:
    """Human-readable BLS breakdown. Official series only — no invented prints."""
    stamp = snapshot.fetched_at.strftime("%Y-%m-%d %H:%M UTC")
    latest_period = max((f"{row.period_name} {row.year}" for row in snapshot.prints), default="")
    lines = [
        "Mr North hourly — Bureau of Labor Statistics",
        f"Fetched {stamp}",
        "",
        f"Official prints (latest: {latest_period})",
    ]
    if unchanged:
        lines.append("No new BLS print this hour — latest official figures unchanged.")
        lines.append("")
    for row in snapshot.prints:
        lines.append(f"• {row.label}: {_format_value(row)}{_format_delta(row)}")
    lines.extend(
        [
            "",
            "Source: U.S. Bureau of Labor Statistics Public Data API v1",
            "https://www.bls.gov/developers/api_signature.htm",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
