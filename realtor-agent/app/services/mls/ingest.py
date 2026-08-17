"""Ingest authorized MLS payloads into normalized listing rows."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.integrations.mls.base import MLSProvider, NormalizedListingDraft
from app.models.enums import ActorOrigin, ActorType
from app.models.listing import Listing
from app.models.mixins import utcnow
from app.models.realtor import Realtor
from app.services.audit import AuditService
from app.services.matching.duplicates import listing_fingerprint
from app.utilities.ids import next_public_id


class ListingIngestService:
    def __init__(self, db: Session, provider: MLSProvider, audit: AuditService | None = None) -> None:
        self.db = db
        self.provider = provider
        self.audit = audit or AuditService(db)

    def sync(self, realtor: Realtor, incremental: bool = True) -> dict:
        if not self.provider.authenticate():
            raise RuntimeError("MLS provider authentication failed")
        since = None
        if incremental:
            latest = (
                self.db.query(Listing)
                .filter(Listing.realtor_id == realtor.id)
                .order_by(Listing.last_seen_at.desc())
                .first()
            )
            since = latest.last_seen_at if latest else None
        raw_items = self.provider.fetch_new_listings(since=since)
        created = 0
        updated = 0
        for raw in raw_items:
            draft = self.provider.normalize_listing(raw)
            result = self.upsert(realtor, draft)
            if result == "created":
                created += 1
            elif result == "updated":
                updated += 1
        self.audit.analytics(realtor.id, "listings_scanned", {"count": len(raw_items), "created": created, "updated": updated})
        return {"scanned": len(raw_items), "created": created, "updated": updated}

    def upsert(self, realtor: Realtor, draft: NormalizedListingDraft) -> str:
        existing = (
            self.db.query(Listing)
            .filter(Listing.realtor_id == realtor.id, Listing.mls_listing_id == draft.mls_listing_id)
            .one_or_none()
        )
        now = utcnow()
        if existing is None:
            listing = Listing(
                public_id=next_public_id(self.db, "LST"),
                realtor_id=realtor.id,
                **_draft_kwargs(draft),
            )
            listing.material_fingerprint = listing_fingerprint(listing)
            listing.status_history = [{"status": listing.listing_status, "at": now.isoformat()}]
            listing.price_history = [{"price": str(listing.asking_price), "at": now.isoformat()}]
            self.db.add(listing)
            self.db.flush()
            self.audit.record(
                event="LISTING_INGESTED",
                object_type="listing",
                object_id=listing.public_id,
                actor="mls_ingest",
                actor_type=ActorType.SYSTEM.value,
                origin=ActorOrigin.AUTOMATION.value,
                realtor_id=str(realtor.id),
                after_state={"mls_listing_id": listing.mls_listing_id},
            )
            self.audit.timeline(
                realtor_id=realtor.id,
                event_type="LISTING_DISCOVERED",
                message=f"MLS listing discovered: {listing.street_address}",
                listing_id=listing.id,
            )
            return "created"

        changed = _apply_draft(existing, draft)
        existing.last_seen_at = now
        if changed:
            existing.listing_version += 1
            existing.material_fingerprint = listing_fingerprint(existing)
            self.audit.timeline(
                realtor_id=realtor.id,
                event_type="LISTING_UPDATED",
                message=f"MLS listing updated: {existing.street_address}",
                listing_id=existing.id,
            )
            return "updated"
        return "unchanged"


def _draft_kwargs(draft: NormalizedListingDraft) -> dict:
    return {
        "mls_listing_id": draft.mls_listing_id,
        "provider": draft.provider,
        "street_address": draft.street_address,
        "city": draft.city,
        "state": draft.state,
        "zip_code": draft.zip_code,
        "neighborhood": draft.neighborhood,
        "latitude": draft.latitude,
        "longitude": draft.longitude,
        "asking_price": draft.asking_price,
        "previous_price": draft.previous_price,
        "property_type": draft.property_type,
        "bedrooms": draft.bedrooms,
        "bathrooms": draft.bathrooms,
        "sqft": draft.sqft,
        "lot_sqft": draft.lot_sqft,
        "year_built": draft.year_built,
        "days_on_market": draft.days_on_market,
        "listing_status": draft.listing_status,
        "listing_date": draft.listing_date,
        "hoa_monthly": draft.hoa_monthly,
        "taxes_annual": draft.taxes_annual,
        "estimated_rent": draft.estimated_rent,
        "cap_rate": draft.cap_rate,
        "grm": draft.grm,
        "occupancy_status": draft.occupancy_status,
        "seller_financing": draft.seller_financing,
        "foreclosure": draft.foreclosure,
        "short_sale": draft.short_sale,
        "assumable_loan": draft.assumable_loan,
        "repair_estimate": draft.repair_estimate,
        "remarks": draft.remarks,
        "agent_remarks": draft.agent_remarks,
        "listing_url": draft.listing_url,
        "photos": draft.photos,
        "raw_payload": draft.raw_payload,
    }


def _apply_draft(listing: Listing, draft: NormalizedListingDraft) -> bool:
    changed = False
    now = datetime.now(timezone.utc).isoformat()
    kwargs = _draft_kwargs(draft)
    if listing.asking_price != draft.asking_price:
        listing.price_history = list(listing.price_history or []) + [
            {"price": str(draft.asking_price), "at": now}
        ]
        listing.previous_price = listing.asking_price
        changed = True
    if listing.listing_status != draft.listing_status:
        listing.status_history = list(listing.status_history or []) + [
            {"status": draft.listing_status, "at": now}
        ]
        changed = True
    for key, value in kwargs.items():
        if key in {"raw_payload", "photos"}:
            if getattr(listing, key) != value:
                setattr(listing, key, value)
            continue
        if getattr(listing, key) != value:
            setattr(listing, key, value)
            changed = True
    listing.raw_payload = draft.raw_payload
    return changed
