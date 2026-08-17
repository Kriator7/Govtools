"""Evaluate listings against active criteria and persist opportunities."""

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import ActorOrigin, ActorType, OpportunityStatus
from app.models.investor import Investor
from app.models.investor_criteria import InvestorCriteria
from app.models.listing import Listing
from app.models.opportunity import Opportunity
from app.models.realtor import Realtor
from app.services.audit import AuditService
from app.services.matching.duplicates import is_material_change, material_fields
from app.services.matching.engine import MatchingEngine
from app.utilities.ids import next_public_id


class OpportunityMatcher:
    def __init__(self, db: Session, engine: MatchingEngine | None = None, audit: AuditService | None = None) -> None:
        self.db = db
        self.engine = engine or MatchingEngine()
        self.audit = audit or AuditService(db)
        self.settings = get_settings()

    def match_listing(self, realtor: Realtor, listing: Listing) -> list[Opportunity]:
        profiles = (
            self.db.query(InvestorCriteria)
            .join(Investor, Investor.id == InvestorCriteria.investor_id)
            .filter(
                InvestorCriteria.realtor_id == realtor.id,
                InvestorCriteria.is_active.is_(True),
                Investor.is_active.is_(True),
            )
            .all()
        )
        created: list[Opportunity] = []
        for criteria in profiles:
            opportunity = self._match_one(realtor, listing, criteria)
            if opportunity is not None:
                created.append(opportunity)
        return created

    def match_all(self, realtor: Realtor) -> list[Opportunity]:
        listings = self.db.query(Listing).filter(Listing.realtor_id == realtor.id).all()
        created: list[Opportunity] = []
        for listing in listings:
            created.extend(self.match_listing(realtor, listing))
        return created

    def _match_one(self, realtor: Realtor, listing: Listing, criteria: InvestorCriteria) -> Opportunity | None:
        result = self.engine.evaluate(listing, criteria)
        if not result.matched:
            return None
        if float(result.score) < self.settings.alert_min_score and not self.settings.alert_below_threshold:
            return None

        existing = (
            self.db.query(Opportunity)
            .filter(
                Opportunity.listing_id == listing.id,
                Opportunity.investor_id == criteria.investor_id,
                Opportunity.criteria_id == criteria.id,
            )
            .order_by(Opportunity.match_version.desc())
            .first()
        )
        snapshot = (existing.explanation or {}).get("listing_snapshot") if existing else None
        if existing and not is_material_change(snapshot, listing):
            return None

        match_version = (existing.match_version + 1) if existing else 1
        investor = self.db.get(Investor, criteria.investor_id)
        explanation = result.as_explanation(investor.name if investor else criteria.name)
        explanation["listing_snapshot"] = material_fields(listing)
        opportunity = Opportunity(
            public_id=next_public_id(self.db, "OPP"),
            realtor_id=realtor.id,
            listing_id=listing.id,
            investor_id=criteria.investor_id,
            criteria_id=criteria.id,
            score=result.score,
            score_category=result.category,
            explanation=explanation,
            status=OpportunityStatus.AWAITING_REALTOR_REVIEW.value,
            match_version=match_version,
            listing_fingerprint=listing.material_fingerprint,
        )
        self.db.add(opportunity)
        self.db.flush()
        self.audit.record(
            event="MATCH_DETECTED",
            object_type="opportunity",
            object_id=opportunity.public_id,
            actor="matching_engine",
            actor_type=ActorType.SYSTEM.value,
            origin=ActorOrigin.AUTOMATION.value,
            realtor_id=str(realtor.id),
            after_state={"score": float(result.score), "investor": investor.name if investor else None},
        )
        self.audit.timeline(
            realtor_id=realtor.id,
            event_type="INVESTOR_MATCHED",
            message=f"Investor match score: {result.score} ({result.category})",
            opportunity_id=opportunity.id,
            listing_id=listing.id,
            investor_id=criteria.investor_id,
        )
        self.audit.analytics(
            realtor.id,
            "listing_matched",
            {"opportunity_id": opportunity.public_id, "score": float(result.score)},
        )
        return opportunity
