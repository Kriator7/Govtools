"""Hunt public seller leads, store them, and optionally ingest FSBO/HUD as listings."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.integrations.mls.base import NormalizedListingDraft
from app.integrations.open_leads.base import OpenLeadDraft
from app.integrations.open_leads.catalog import SOURCE_NAMES, providers_for
from app.models.enums import ActorOrigin, ActorType
from app.models.realtor import Realtor
from app.models.seller_lead import SellerLead
from app.services.audit import AuditService
from app.services.matching.runner import OpportunityMatcher
from app.services.mls.ingest import ListingIngestService
from app.utilities.ids import next_public_id

LISTABLE_SOURCES = frozenset({"fsbo", "hud"})


class OpenLeadHuntService:
    def __init__(self, db: Session, audit: AuditService | None = None) -> None:
        self.db = db
        self.audit = audit or AuditService(db)

    def hunt(self, realtor: Realtor, *, source: str | None = None, mode: str | None = None) -> dict:
        if source and source not in SOURCE_NAMES:
            raise ValueError(f"Unknown open-lead source {source!r}. Use one of: {', '.join(SOURCE_NAMES)}")
        scanned = 0
        created = 0
        converted = 0
        errors: list[str] = []
        by_source: dict[str, int] = {}
        new_leads: list[SellerLead] = []
        for provider in providers_for(source, mode=mode):
            try:
                drafts = provider.search()
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{provider.name}: {exc}")
                continue
            for draft in drafts:
                scanned += 1
                lead, was_created = self.upsert(realtor, draft)
                by_source[lead.source] = by_source.get(lead.source, 0) + 1
                if was_created:
                    created += 1
                    new_leads.append(lead)
                    if self._maybe_convert(realtor, lead, draft):
                        converted += 1
        self.audit.analytics(
            realtor.id,
            "open_leads_hunted",
            {"scanned": scanned, "created": created, "converted": converted, "source": source or "all"},
        )
        return {
            "ok": True,
            "scanned": scanned,
            "created": created,
            "converted": converted,
            "by_source": by_source,
            "errors": errors,
            "lead_ids": [lead.public_id for lead in new_leads],
        }

    def upsert(self, realtor: Realtor, draft: OpenLeadDraft) -> tuple[SellerLead, bool]:
        existing = (
            self.db.query(SellerLead)
            .filter(SellerLead.realtor_id == realtor.id, SellerLead.fingerprint == draft.fingerprint)
            .one_or_none()
        )
        if existing is not None:
            _apply_draft(existing, draft)
            return existing, False
        lead = SellerLead(
            public_id=next_public_id(self.db, "LED"),
            realtor_id=realtor.id,
            source=draft.source,
            status="new",
            title=draft.title,
            summary=draft.summary,
            url=draft.url,
            fingerprint=draft.fingerprint,
            city=draft.city,
            state=draft.state,
            zip_code=draft.zip_code,
            person_name=draft.person_name,
            street_address=draft.street_address,
            asking_price=draft.asking_price,
            published_at=draft.published_at,
            review_only=draft.review_only,
            assessor_url=draft.assessor_url,
            raw_payload=draft.raw_payload,
        )
        self.db.add(lead)
        self.db.flush()
        self.audit.record(
            event="SELLER_LEAD_DISCOVERED",
            object_type="seller_lead",
            object_id=lead.public_id,
            actor="open_lead_hunt",
            actor_type=ActorType.SYSTEM.value,
            origin=ActorOrigin.AUTOMATION.value,
            realtor_id=str(realtor.id),
            after_state={"source": lead.source, "review_only": lead.review_only},
        )
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type="SELLER_LEAD_DISCOVERED",
            message=f"{lead.source} lead: {lead.title}",
        )
        return lead, True

    def recent(self, realtor: Realtor, *, source: str | None = None, limit: int = 12) -> list[SellerLead]:
        query = self.db.query(SellerLead).filter(SellerLead.realtor_id == realtor.id)
        if source:
            query = query.filter(SellerLead.source == source)
        return query.order_by(SellerLead.created_at.desc()).limit(limit).all()

    def get(self, realtor: Realtor, public_id: str) -> SellerLead | None:
        return (
            self.db.query(SellerLead)
            .filter(SellerLead.realtor_id == realtor.id, SellerLead.public_id == public_id)
            .one_or_none()
        )

    def set_status(self, realtor: Realtor, public_id: str, status: str) -> SellerLead | None:
        lead = self.get(realtor, public_id)
        if lead is None:
            return None
        lead.status = status
        return lead

    def _maybe_convert(self, realtor: Realtor, lead: SellerLead, draft: OpenLeadDraft) -> bool:
        if lead.listing_id is not None:
            return False
        if lead.source not in LISTABLE_SOURCES or not draft.can_become_listing:
            return False
        from app.models.listing import Listing

        ingest = ListingIngestService(self.db, _OpenListingAdapter())
        listing_id = f"OPEN-{draft.source}-{draft.fingerprint[:12]}"
        ingest.upsert(realtor, _listing_draft(draft, listing_id))
        listing = (
            self.db.query(Listing)
            .filter(Listing.realtor_id == realtor.id, Listing.mls_listing_id == listing_id)
            .one_or_none()
        )
        if listing is None:
            return False
        lead.listing_id = listing.id
        lead.status = "converted"
        OpportunityMatcher(self.db).match_listing(realtor, listing)
        return True


class _OpenListingAdapter:
    """ListingIngestService requires an MLSProvider; open leads only use upsert()."""

    name = "open"

    def authenticate(self) -> bool:
        return True

    def fetch_new_listings(self, since=None):
        return []

    def fetch_updated_listings(self, since=None):
        return []

    def get_listing(self, mls_listing_id: str):
        return None

    def normalize_listing(self, raw):
        raise RuntimeError("Open-lead ingest uses upsert(draft) directly")


def _listing_draft(draft: OpenLeadDraft, listing_id: str) -> NormalizedListingDraft:
    return NormalizedListingDraft(
        mls_listing_id=listing_id,
        street_address=draft.street_address or draft.title,
        city=draft.city or "Las Vegas",
        state=draft.state or "NV",
        zip_code=draft.zip_code or "00000",
        asking_price=draft.asking_price or Decimal("0"),
        property_type=draft.property_type,
        listing_status="active",
        remarks=draft.summary,
        listing_url=draft.url,
        raw_payload=draft.raw_payload,
        provider=draft.source,
        foreclosure=draft.source in {"hud", "probate"},
    )


def _apply_draft(lead: SellerLead, draft: OpenLeadDraft) -> None:
    lead.title = draft.title
    lead.summary = draft.summary
    lead.url = draft.url
    lead.city = draft.city or lead.city
    lead.person_name = draft.person_name or lead.person_name
    lead.street_address = draft.street_address or lead.street_address
    lead.asking_price = draft.asking_price if draft.asking_price is not None else lead.asking_price
    lead.assessor_url = draft.assessor_url or lead.assessor_url
    lead.raw_payload = draft.raw_payload
