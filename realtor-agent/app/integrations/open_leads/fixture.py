"""Fixture open leads so hunt works without network (OPEN_LEADS_MODE=fixture)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT
from app.integrations.open_leads.base import OpenLeadDraft, OpenLeadProvider
from app.integrations.open_leads.market import assessor_search_url
from app.integrations.open_leads.rss import fingerprint_for, parse_datetime

DEFAULT_FIXTURE = PROJECT_ROOT / "data" / "imports" / "sample_open_leads.json"


class FixtureOpenLeadProvider(OpenLeadProvider):
    name = "fixture"

    def __init__(self, fixture_path: Path | None = None, *, source: str | None = None) -> None:
        self.fixture_path = fixture_path or DEFAULT_FIXTURE
        self.source_filter = source

    def search(self) -> list[OpenLeadDraft]:
        if not self.fixture_path.exists():
            return []
        raw_items = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        drafts: list[OpenLeadDraft] = []
        for raw in raw_items:
            draft = _from_raw(raw)
            if self.source_filter and draft.source != self.source_filter:
                continue
            drafts.append(draft)
        return drafts


def _from_raw(raw: dict[str, Any]) -> OpenLeadDraft:
    published = parse_datetime(raw.get("published_at")) or datetime.now(timezone.utc)
    price = Decimal(str(raw["asking_price"])) if raw.get("asking_price") is not None else None
    title = str(raw["title"])
    url = str(raw["url"])
    source = str(raw["source"])
    person = raw.get("person_name")
    street = raw.get("street_address")
    return OpenLeadDraft(
        source=source,
        title=title,
        summary=str(raw.get("summary") or title),
        url=url,
        fingerprint=str(raw.get("fingerprint") or fingerprint_for(source, url, title)),
        city=raw.get("city"),
        state=str(raw.get("state") or "NV"),
        zip_code=raw.get("zip_code"),
        person_name=person,
        street_address=street,
        asking_price=price,
        published_at=published,
        property_type=str(raw.get("property_type") or "single_family"),
        review_only=bool(raw.get("review_only", source in {"obituary", "probate"})),
        assessor_url=raw.get("assessor_url") or assessor_search_url(person or street or title),
        raw_payload=raw,
    )
