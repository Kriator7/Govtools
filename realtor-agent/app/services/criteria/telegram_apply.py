"""Apply Damian Telegram buy-box notes to the investor on the last listing card.

Relays stay on. Do not SMS Damian or investors.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.models.enums import ActorOrigin, ActorType, OpportunityStatus, RejectionReason
from app.models.investor import Investor
from app.models.investor_criteria import InvestorCriteria
from app.models.listing import Listing
from app.models.opportunity import Opportunity
from app.models.realtor import Realtor
from app.services.audit import AuditService
from app.services.matching.engine import MatchingEngine
from app.services.matching.screening import (
    PIRATES_CITIES,
    PIRATES_MAX_PRICE_PCT_OF_ARV,
    normalize_property_type,
)
from app.services.seed import find_damian_realtor
from app.services.telegram.notes import extract_opportunity_id, format_note_confirmation, parse_realtor_note
from app.utilities.ids import next_public_id
from app.utilities.money import money_label

STRETCH_PROFILE_NAME = "Stretch / very good deal"
TELEGRAM_PROFILE_LABELS = {
    "condo": "Telegram condo",
    "single_family": "Telegram SFH",
    "multi_family": "Telegram multi-family",
    "townhouse": "Telegram townhouse",
}
HOLD_NOTE = (
    "Buy-and-hold rentals held for a long time. Not a flip. "
    "Telegram note from Damian Einbinder."
)
NOTES_PATH = PROJECT_ROOT / "data" / "telegram" / "notes.jsonl"


class TelegramCriteriaService:
    def __init__(self, db: Session, audit: AuditService | None = None) -> None:
        self.db = db
        self.audit = audit or AuditService(db)
        self.engine = MatchingEngine()

    def remember_opportunity(self, realtor: Realtor, opportunity_id: str) -> None:
        settings = dict(realtor.notification_settings or {})
        settings["last_telegram_opportunity_id"] = opportunity_id
        realtor.notification_settings = settings
        self.db.flush()

    def apply_note(
        self,
        realtor: Realtor,
        text: str,
        *,
        payload: dict | None = None,
        from_user: dict | None = None,
    ) -> dict:
        parsed = parse_realtor_note(text)
        _append_note_log(parsed, from_user)
        investor = self._resolve_investor(realtor, parsed, payload)
        if investor is None:
            return {"ok": False, "error": "no investor on the last listing card", "parsed": parsed}
        if not parsed.get("has_criteria"):
            return {
                "ok": True,
                "saved": True,
                "applied": False,
                "parsed": parsed,
                "investor": investor.name,
                "reply": "Saved your note. I did not find a price or strategy change in that message.",
            }

        applied = self._apply_parsed(realtor, investor, parsed)
        applied["investor"] = investor.name
        applied["buy_and_hold"] = bool(parsed.get("buy_and_hold") or applied.get("buy_and_hold"))
        self._copy_to_damian(parsed, applied)
        self.audit.record(
            event="TELEGRAM_CRITERIA_UPDATED",
            object_type="investor",
            object_id=investor.public_id,
            actor=(from_user or {}).get("username") or "telegram",
            actor_type=ActorType.REALTOR.value,
            origin=ActorOrigin.HUMAN.value,
            realtor_id=str(realtor.id),
            after_state={
                "min_price": str(applied.get("min_price") or ""),
                "max_price": str(applied.get("max_price") or ""),
                "buy_and_hold": applied.get("buy_and_hold"),
                "stretch": bool(applied.get("stretch")),
                "property_types": applied.get("property_types") or [],
                "max_price_pct_of_arv": str(applied.get("max_price_pct_of_arv") or ""),
                "telegram_profile": applied.get("telegram_profile"),
            },
            detail=parsed.get("raw"),
        )
        return {
            "ok": True,
            "applied": True,
            "parsed": parsed,
            "investor": investor.name,
            "result": applied,
            "reply": format_note_confirmation(applied),
        }

    def _resolve_investor(self, realtor: Realtor, parsed: dict, payload: dict | None) -> Investor | None:
        payload = payload or {}
        message = payload.get("message") or payload.get("edited_message") or {}
        reply = message.get("reply_to_message") or {}
        opp_id = (
            parsed.get("opportunity_id")
            or extract_opportunity_id(reply.get("text"), reply.get("caption"))
            or (realtor.notification_settings or {}).get("last_telegram_opportunity_id")
        )
        if opp_id:
            opportunity = (
                self.db.query(Opportunity)
                .filter(Opportunity.public_id == opp_id, Opportunity.realtor_id == realtor.id)
                .one_or_none()
            )
            if opportunity is not None:
                investor = self.db.get(Investor, opportunity.investor_id)
                if investor is not None:
                    return investor
        return (
            self.db.query(Investor)
            .filter(Investor.realtor_id == realtor.id, Investor.name == "ABC Capital")
            .one_or_none()
        )

    def _apply_parsed(self, realtor: Realtor, investor: Investor, parsed: dict) -> dict:
        types = [normalize_property_type(item) for item in (parsed.get("property_types") or [])]
        arv_pct = parsed.get("max_price_pct_of_arv")
        min_price = parsed.get("min_price")
        max_price = parsed.get("max_price")
        typed_profile = None
        profiles: list[InvestorCriteria] = []
        if types or arv_pct is not None:
            typed_profile = self._upsert_telegram_profile(realtor, investor, parsed, types, arv_pct)
            profiles = [typed_profile]
        else:
            profiles = (
                self.db.query(InvestorCriteria)
                .filter(
                    InvestorCriteria.investor_id == investor.id,
                    InvestorCriteria.is_active.is_(True),
                    InvestorCriteria.name != STRETCH_PROFILE_NAME,
                    ~InvestorCriteria.name.startswith("Telegram "),
                )
                .all()
            )
            for profile in profiles:
                before_min = profile.min_price
                before_max = profile.max_price
                if min_price is not None:
                    profile.min_price = min_price
                if max_price is not None:
                    profile.max_price = max_price
                    profile.max_purchase_price = max_price
                if parsed.get("buy_and_hold"):
                    profile.rehab_tolerance = "buy_and_hold"
                    profile.notes = _merge_note(profile.notes, HOLD_NOTE)
                    profile.nl_criteria = (
                        "Primary box is buy-and-hold rentals. "
                        f"{money_label(profile.min_price)} to {money_label(profile.max_price)}. Not a flip."
                    )
                    if "value-add" in (profile.name or "").lower():
                        profile.name = profile.name.replace("value-add", "buy-and-hold")
                if min_price is not None or max_price is not None:
                    strict = list(profile.strict_fields or [])
                    for field_name in ("min_price", "max_price"):
                        if field_name not in strict:
                            strict.append(field_name)
                    profile.strict_fields = strict
                self.db.flush()
                if not min_price:
                    min_price = profile.min_price or before_min
                if not max_price:
                    max_price = profile.max_price or before_max

        stretch = None
        if parsed.get("stretch_over_max") and typed_profile is None:
            stretch = self._upsert_stretch(realtor, investor, profiles, max_price)
        rejected = self._rescreen_pending(realtor, investor)
        search = self._mls_search_status(realtor, typed_profile) if typed_profile is not None else None
        return {
            "min_price": min_price,
            "max_price": max_price,
            "buy_and_hold": bool(parsed.get("buy_and_hold")),
            "stretch": stretch,
            "rejected": rejected,
            "profiles": [item.name for item in profiles],
            "property_types": list(typed_profile.property_types or []) if typed_profile else types,
            "max_price_pct_of_arv": typed_profile.max_price_pct_of_arv if typed_profile else arv_pct,
            "telegram_profile": typed_profile.name if typed_profile else None,
            "search": search,
        }

    def _upsert_telegram_profile(
        self,
        realtor: Realtor,
        investor: Investor,
        parsed: dict,
        types: list[str],
        arv_pct: Decimal | None,
    ) -> InvestorCriteria:
        name = _telegram_profile_name(types)
        profile = (
            self.db.query(InvestorCriteria)
            .filter(
                InvestorCriteria.investor_id == investor.id,
                InvestorCriteria.name == name,
            )
            .one_or_none()
        )
        if profile is None:
            profile = InvestorCriteria(
                public_id=next_public_id(self.db, "CRT"),
                realtor_id=realtor.id,
                investor_id=investor.id,
                name=name,
                is_active=True,
            )
            self.db.add(profile)
        profile.cities = list(PIRATES_CITIES)
        profile.geographic_area = "Las Vegas; North Las Vegas; Henderson"
        if types:
            profile.property_types = types
        if arv_pct is not None:
            profile.max_price_pct_of_arv = arv_pct
        if parsed.get("min_price") is not None:
            profile.min_price = parsed["min_price"]
        if parsed.get("max_price") is not None:
            profile.max_price = parsed["max_price"]
            profile.max_purchase_price = parsed["max_price"]
        if parsed.get("buy_and_hold"):
            profile.rehab_tolerance = "buy_and_hold"
        profile.hoa_required = None
        profile.strict_fields = _telegram_strict_fields(types, arv_pct, parsed)
        profile.notes = _merge_note(
            profile.notes,
            (
                "Telegram typed buy box. Separate from the $300k–$600k SFH/MF box "
                "and from Pirates 80% SFH. Condos may have HOA. Do not invent ARV."
            ),
        )
        type_label = ", ".join(types) if types else "listings"
        pct_label = f"{float(arv_pct) * 100:.0f}% of ARV" if arv_pct is not None else "stated ARV rules"
        profile.nl_criteria = (
            f"{type_label} in Las Vegas, North Las Vegas, or Henderson. "
            f"Max purchase {pct_label}. ARV is not invented."
        )
        profile.is_active = True
        self.db.flush()
        return profile

    def _mls_search_status(self, realtor: Realtor, profile: InvestorCriteria) -> dict:
        """Search only when a live MLS provider is connected. Mock is not live MLS."""
        from app.services.providers import get_mls_provider

        provider = get_mls_provider()
        name = str(getattr(provider, "name", "mock") or "mock")
        if name == "mock":
            return {
                "provider": "mock",
                "connected": False,
                "matched": 0,
                "opportunity_ids": [],
                "profile": profile.name,
            }
        from app.services.matching.runner import OpportunityMatcher
        from app.services.mls.ingest import ListingIngestService

        ListingIngestService(self.db, provider).sync(realtor, incremental=False)
        self.db.flush()
        created = OpportunityMatcher(self.db).match_profile(realtor, profile)
        return {
            "provider": name,
            "connected": True,
            "matched": len(created),
            "opportunity_ids": [item.public_id for item in created],
            "profile": profile.name,
        }

    def _upsert_stretch(
        self,
        realtor: Realtor,
        investor: Investor,
        primary: list[InvestorCriteria],
        primary_max: Decimal | None,
    ) -> dict:
        floor = primary_max or Decimal("600000")
        cities: list[str] = []
        types: list[str] = []
        for profile in primary:
            for city in profile.cities or []:
                if city not in cities:
                    cities.append(city)
            for item in profile.property_types or []:
                if item not in types:
                    types.append(item)
        stretch = (
            self.db.query(InvestorCriteria)
            .filter(
                InvestorCriteria.investor_id == investor.id,
                InvestorCriteria.name == STRETCH_PROFILE_NAME,
            )
            .one_or_none()
        )
        if stretch is None:
            stretch = InvestorCriteria(
                public_id=next_public_id(self.db, "CRT"),
                realtor_id=realtor.id,
                investor_id=investor.id,
                name=STRETCH_PROFILE_NAME,
                is_active=True,
            )
            self.db.add(stretch)
        stretch.min_price = floor
        stretch.max_price = Decimal("1200000")
        stretch.max_purchase_price = None
        stretch.cities = cities or ["Las Vegas", "Henderson"]
        stretch.property_types = types or ["single_family", "multi_family"]
        stretch.max_price_pct_of_arv = PIRATES_MAX_PRICE_PCT_OF_ARV
        stretch.rehab_tolerance = "buy_and_hold"
        stretch.strict_fields = ["min_price", "max_price_pct_of_arv", "cities", "property_types"]
        stretch.notes = (
            f"Over {money_label(floor)} only if it is a very good deal. "
            f"Price ÷ ARV must be ≤ {float(PIRATES_MAX_PRICE_PCT_OF_ARV) * 100:.0f}%. "
            "Different parameters from the $300k–$600k core box. Not a flip."
        )
        stretch.nl_criteria = stretch.notes
        self.db.flush()
        return {
            "name": stretch.name,
            "min_price": stretch.min_price,
            "max_price": stretch.max_price,
            "max_price_pct_of_arv": stretch.max_price_pct_of_arv,
        }

    def _rescreen_pending(self, realtor: Realtor, investor: Investor) -> list[str]:
        pending = (
            self.db.query(Opportunity)
            .filter(
                Opportunity.realtor_id == realtor.id,
                Opportunity.investor_id == investor.id,
                Opportunity.status.in_(
                    [
                        OpportunityStatus.AWAITING_REALTOR_REVIEW.value,
                        OpportunityStatus.MATCH_DETECTED.value,
                        OpportunityStatus.AWAITING_ARV.value,
                    ]
                ),
            )
            .all()
        )
        rejected: list[str] = []
        for opportunity in pending:
            listing = self.db.get(Listing, opportunity.listing_id)
            criteria = self.db.get(InvestorCriteria, opportunity.criteria_id)
            if listing is None or criteria is None:
                continue
            result = self.engine.evaluate(listing, criteria)
            if result.matched:
                opportunity.score = result.score
                opportunity.explanation = result.as_explanation(investor.name)
                continue
            opportunity.status = OpportunityStatus.REJECTED.value
            opportunity.rejection_reason = RejectionReason.TOO_EXPENSIVE.value
            opportunity.rejection_notes = "Rejected after Damian Telegram buy-box update."
            rejected.append(
                f"{opportunity.public_id} ({listing.street_address} {money_label(listing.asking_price)})"
            )
            self.audit.timeline(
                realtor_id=realtor.id,
                event_type="REJECT_OPPORTUNITY",
                message=f"Rescreen rejected {opportunity.public_id} after Damian buy-box note",
                opportunity_id=opportunity.id,
                listing_id=listing.id,
                investor_id=investor.id,
                actor_type=ActorType.REALTOR.value,
            )
        self.db.flush()
        return rejected

    def _copy_to_damian(self, parsed: dict, applied: dict) -> None:
        damian = find_damian_realtor(self.db)
        if damian is None:
            return
        parts: list[str] = []
        if parsed.get("property_types") or parsed.get("max_price_pct_of_arv") is not None:
            types = parsed.get("property_types") or []
            pct = parsed.get("max_price_pct_of_arv")
            bit = "typed box on ABC Capital test flow (not Pirates 80% SFH)"
            if types:
                bit += ": " + ", ".join(types)
            if pct is not None:
                bit += f"; max {float(pct) * 100:.0f}% of ARV"
            parts.append(bit)
        if parsed.get("min_price") or parsed.get("max_price") or parsed.get("buy_and_hold"):
            parts.append(
                f"{money_label(applied.get('min_price'))}–{money_label(applied.get('max_price'))} "
                "buy-and-hold; stretch over max only for a very good deal."
            )
        if not parts:
            return
        summary = "Telegram buy-box note: " + " ".join(parts)
        existing = damian.notes or ""
        if summary not in existing:
            damian.notes = f"{existing}\n{summary}".strip()
        self.db.flush()


def _merge_note(existing: str | None, extra: str) -> str:
    current = (existing or "").strip()
    if extra in current:
        return current
    return f"{current}\n{extra}".strip()


def _telegram_profile_name(types: list[str]) -> str:
    if len(types) == 1 and types[0] in TELEGRAM_PROFILE_LABELS:
        return TELEGRAM_PROFILE_LABELS[types[0]]
    if types:
        return "Telegram " + "+".join(types)
    return "Telegram ARV"


def _telegram_strict_fields(types: list[str], arv_pct: Decimal | None, parsed: dict) -> list[str]:
    fields = ["cities"]
    if types:
        fields.append("property_types")
    if arv_pct is not None:
        fields.append("max_price_pct_of_arv")
    if parsed.get("min_price") is not None:
        fields.append("min_price")
    if parsed.get("max_price") is not None:
        fields.append("max_price")
    return fields


def _append_note_log(parsed: dict, from_user: dict | None) -> None:
    import json
    from datetime import datetime, timezone

    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "at": datetime.now(timezone.utc).isoformat(),
        "from": (from_user or {}).get("username"),
        "telegram_user_id": (from_user or {}).get("id"),
        "parsed": {
            "min_price": str(parsed.get("min_price") or ""),
            "max_price": str(parsed.get("max_price") or ""),
            "buy_and_hold": parsed.get("buy_and_hold"),
            "stretch_over_max": parsed.get("stretch_over_max"),
            "property_types": parsed.get("property_types") or [],
            "max_price_pct_of_arv": str(parsed.get("max_price_pct_of_arv") or ""),
            "opportunity_id": parsed.get("opportunity_id"),
        },
        "raw": parsed.get("raw"),
    }
    with NOTES_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")
