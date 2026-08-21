"""Apply Damian Telegram buy-box notes to the investor on the last listing card.

Relays stay on. Do not SMS Damian or investors.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID

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
ADDITIONAL_NOTE = "Telegram lane: additional (not the main box)."
LOW_PRIORITY_NOTE = "Telegram priority: low. Not a priority; do not lead search with this box."
MAIN_SFH_NOTE = "Main Telegram-confirmed box: single-family, no HOA."
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
                "main_box": applied.get("main_box"),
                "additional_box": applied.get("additional_box"),
                "low_priority": bool(applied.get("low_priority")),
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
        mentions_main = bool(parsed.get("mentions_main"))
        mentions_additional = bool(parsed.get("mentions_additional"))
        low_priority = bool(parsed.get("low_priority"))
        no_hoa = parsed.get("hoa_required") is False
        typed_profile = None
        additional_profile = None
        main_profiles: list[InvestorCriteria] = []
        profiles: list[InvestorCriteria] = []
        create_typed = bool(types or arv_pct is not None) and not mentions_main
        ranking = mentions_main or mentions_additional or low_priority

        if create_typed:
            typed_profile = self._upsert_telegram_profile(realtor, investor, parsed, types, arv_pct)
            self._remember_telegram_profile(realtor, typed_profile)
            profiles = [typed_profile]
            if mentions_additional:
                additional_profile = self._mark_additional(typed_profile)

        if mentions_additional and additional_profile is None:
            additional_profile = self._last_telegram_profile(realtor, investor)
            if additional_profile is not None:
                self._mark_additional(additional_profile)
                self._remember_telegram_profile(realtor, additional_profile)

        if mentions_main and (not types or "single_family" in types):
            main_profiles = self._confirm_main_sfh_no_hoa(investor, no_hoa=no_hoa)
        elif no_hoa and "single_family" in types:
            main_profiles = self._confirm_main_sfh_no_hoa(investor, no_hoa=True)

        if low_priority:
            target = additional_profile or typed_profile or self._last_telegram_profile(realtor, investor)
            if target is not None:
                self._mark_low_priority(target)
                additional_profile = target

        if not create_typed and not ranking:
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
        if parsed.get("stretch_over_max") and typed_profile is None and not ranking:
            stretch = self._upsert_stretch(realtor, investor, profiles, max_price)
        should_rescreen = (not ranking) or bool(main_profiles)
        rejected = self._rescreen_pending(realtor, investor) if should_rescreen else []
        search_profile = None
        if not low_priority:
            if main_profiles:
                search_profile = main_profiles[0]
            elif typed_profile is not None and additional_profile is None:
                search_profile = typed_profile
        search = None
        if typed_profile is not None or ranking or search_profile is not None:
            search = self._mls_search_status(realtor, search_profile or typed_profile or additional_profile)
        return {
            "min_price": min_price,
            "max_price": max_price,
            "buy_and_hold": bool(parsed.get("buy_and_hold")),
            "stretch": stretch,
            "rejected": rejected,
            "profiles": [item.name for item in (profiles or main_profiles or ([additional_profile] if additional_profile else []))],
            "property_types": list(typed_profile.property_types or []) if typed_profile else types,
            "max_price_pct_of_arv": typed_profile.max_price_pct_of_arv if typed_profile else arv_pct,
            "telegram_profile": typed_profile.name if typed_profile else (
                additional_profile.name if additional_profile else None
            ),
            "main_box": "single-family, no HOA" if main_profiles else None,
            "additional_box": _profile_summary(additional_profile) if additional_profile else None,
            "low_priority": low_priority and additional_profile is not None,
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

    def _remember_telegram_profile(self, realtor: Realtor, profile: InvestorCriteria) -> None:
        settings = dict(realtor.notification_settings or {})
        settings["last_telegram_profile_id"] = str(profile.id)
        settings["last_telegram_profile_name"] = profile.name
        realtor.notification_settings = settings
        self.db.flush()

    def _last_telegram_profile(self, realtor: Realtor, investor: Investor) -> InvestorCriteria | None:
        settings = realtor.notification_settings or {}
        raw_id = settings.get("last_telegram_profile_id")
        if raw_id:
            try:
                profile = self.db.get(InvestorCriteria, UUID(str(raw_id)))
            except (TypeError, ValueError):
                profile = None
            if profile is not None and profile.investor_id == investor.id:
                return profile
        return (
            self.db.query(InvestorCriteria)
            .filter(
                InvestorCriteria.investor_id == investor.id,
                InvestorCriteria.name.startswith("Telegram "),
            )
            .order_by(InvestorCriteria.updated_at.desc())
            .first()
        )

    def _mark_additional(self, profile: InvestorCriteria) -> InvestorCriteria:
        profile.notes = _merge_note(profile.notes, ADDITIONAL_NOTE)
        profile.nl_criteria = _merge_note(profile.nl_criteria, "Additional buy box; not the main search.")
        self.db.flush()
        return profile

    def _mark_low_priority(self, profile: InvestorCriteria) -> InvestorCriteria:
        profile.notes = _merge_note(profile.notes, LOW_PRIORITY_NOTE)
        profile.nl_criteria = _merge_note(
            profile.nl_criteria,
            "Low priority. Do not lead MLS search or listing cards with this box.",
        )
        self.db.flush()
        return profile

    def _confirm_main_sfh_no_hoa(self, investor: Investor, *, no_hoa: bool) -> list[InvestorCriteria]:
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
        updated: list[InvestorCriteria] = []
        for profile in profiles:
            if not _is_sfh_profile(profile):
                continue
            if no_hoa:
                profile.hoa_required = False
                strict = list(profile.strict_fields or [])
                for field_name in ("property_types", "hoa_required"):
                    if field_name not in strict:
                        strict.append(field_name)
                profile.strict_fields = strict
            if not profile.property_types:
                profile.property_types = ["single_family"]
            profile.notes = _merge_note(profile.notes, MAIN_SFH_NOTE)
            updated.append(profile)
        self.db.flush()
        return updated

    def _mls_search_status(self, realtor: Realtor, profile: InvestorCriteria | None) -> dict:
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
                "profile": profile.name if profile is not None else "main",
            }
        from app.services.matching.runner import OpportunityMatcher
        from app.services.mls.ingest import ListingIngestService

        ListingIngestService(self.db, provider).sync(realtor, incremental=False)
        self.db.flush()
        if profile is None:
            return {
                "provider": name,
                "connected": True,
                "matched": 0,
                "opportunity_ids": [],
                "profile": "main",
            }
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
        if parsed.get("mentions_main") or parsed.get("hoa_required") is False:
            parts.append("main box remains single-family, no HOA (as discussed); Pirates 80% SFH unchanged")
        if parsed.get("mentions_additional") or parsed.get("low_priority"):
            extra = applied.get("additional_box") or "typed Telegram box"
            if parsed.get("low_priority"):
                parts.append(f"{extra} is additional and not a priority")
            else:
                parts.append(f"{extra} is additional, not the main box")
        if (parsed.get("property_types") or parsed.get("max_price_pct_of_arv") is not None) and not parsed.get(
            "mentions_main"
        ):
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


def _is_sfh_profile(profile: InvestorCriteria) -> bool:
    types = [normalize_property_type(item) for item in (profile.property_types or [])]
    if types:
        return "single_family" in types and "condo" not in types and "multi_family" not in types
    name = (profile.name or "").lower()
    return "single-family" in name or "single family" in name or "sfh" in name


def _profile_summary(profile: InvestorCriteria | None) -> str | None:
    if profile is None:
        return None
    types = [normalize_property_type(item) for item in (profile.property_types or [])]
    bits = [profile.name]
    if types:
        bits.append(", ".join(types))
    pct = profile.max_price_pct_of_arv
    if pct is not None:
        bits.append(f"max {float(pct) * 100:.0f}% of ARV")
    return " — ".join(bits)


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
