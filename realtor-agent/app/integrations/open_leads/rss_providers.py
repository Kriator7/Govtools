"""Public RSS providers for PirateEye open-lead hunt."""

from __future__ import annotations

from typing import Any, Callable

import httpx

from app.integrations.open_leads.base import OpenLeadDraft, OpenLeadProvider
from app.integrations.open_leads.market import (
    assessor_search_url,
    city_from_text,
    fsbo_rss_url,
    hud_rss_url,
    obituary_rss_url,
    probate_rss_url,
)
from app.integrations.open_leads.parse import (
    asking_price_from_text,
    person_from_obituary_title,
    street_from_text,
)
from app.integrations.open_leads.rss import fetch_text, fingerprint_for, parse_datetime, parse_feed_items

GetText = Callable[[str], str]


class RssOpenLeadProvider(OpenLeadProvider):
    def __init__(
        self,
        *,
        feed_url: str,
        source: str,
        review_only: bool = False,
        get_text: GetText | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.feed_url = feed_url
        self.source = source
        self.review_only = review_only
        self.name = source
        self._get_text = get_text
        self._client = client

    def search(self) -> list[OpenLeadDraft]:
        xml_text = self._read()
        drafts: list[OpenLeadDraft] = []
        for item in parse_feed_items(xml_text):
            draft = self._to_draft(item)
            if draft is not None:
                drafts.append(draft)
        return drafts

    def _read(self) -> str:
        if self._get_text is not None:
            return self._get_text(self.feed_url)
        return fetch_text(self.feed_url, client=self._client)

    def _to_draft(self, item: dict[str, Any]) -> OpenLeadDraft | None:
        title = str(item.get("title") or "").strip()
        url = str(item.get("link") or "").strip()
        if not title or not url:
            return None
        summary = str(item.get("description") or title)
        blob = f"{title} {summary}"
        city = city_from_text(blob)
        person = person_from_obituary_title(title) if self.source == "obituary" else None
        street = None if self.review_only else street_from_text(blob)
        price = None if self.review_only else asking_price_from_text(blob)
        assessor = assessor_search_url(person or street or title)
        return OpenLeadDraft(
            source=self.source,
            title=title[:300],
            summary=summary[:800],
            url=url[:500],
            fingerprint=fingerprint_for(self.source, url, title),
            city=city,
            person_name=person,
            street_address=street,
            asking_price=price,
            published_at=parse_datetime(item.get("published")),
            review_only=self.review_only,
            assessor_url=assessor,
            raw_payload={"feed": self.feed_url, "item": item},
        )


def obituary_provider(**kwargs: Any) -> RssOpenLeadProvider:
    return RssOpenLeadProvider(
        feed_url=obituary_rss_url(),
        source="obituary",
        review_only=True,
        **kwargs,
    )


def fsbo_provider(**kwargs: Any) -> RssOpenLeadProvider:
    return RssOpenLeadProvider(
        feed_url=fsbo_rss_url(),
        source="fsbo",
        review_only=False,
        **kwargs,
    )


def hud_provider(**kwargs: Any) -> RssOpenLeadProvider:
    return RssOpenLeadProvider(
        feed_url=hud_rss_url(),
        source="hud",
        review_only=False,
        **kwargs,
    )


def probate_provider(**kwargs: Any) -> RssOpenLeadProvider:
    return RssOpenLeadProvider(
        feed_url=probate_rss_url(),
        source="probate",
        review_only=True,
        **kwargs,
    )
