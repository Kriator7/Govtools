from sqlalchemy.orm import Session

from app.models.enums import ActorOrigin, ActorType
from app.models.investor import Investor
from app.models.investor_criteria import PIRATES_IG_STRICT_FIELDS, InvestorCriteria
from app.models.realtor import Realtor
from app.services.audit import AuditService
from app.services.matching.screening import PIRATES_CITIES, PIRATES_MAX_PRICE_PCT_OF_ARV
from app.utilities.ids import next_public_id


def seed_realtor(db: Session) -> Realtor:
    existing = db.query(Realtor).filter(Realtor.is_active.is_(True)).order_by(Realtor.created_at.asc()).first()
    if existing:
        if existing.name == "Nevada Demo Realtor":
            existing.name = "Damian Einbinder"
            existing.brokerage = "Home Finder Realty"
            existing.license_number = "B.0146854"
            existing.phone = "+17023710950"
            existing.email = "binder@thehomefinderlv.com"
            existing.notes = "Buyer-side investor work. License expires 2027-07-31."
            db.flush()
        return existing
    realtor = Realtor(
        public_id=next_public_id(db, "RLT"),
        name="Damian Einbinder",
        brokerage="Home Finder Realty",
        license_number="B.0146854",
        license_state="NV",
        phone="+17023710950",
        email="binder@thehomefinderlv.com",
        telegram_chat_id="mock-realtor",
        timezone="America/Los_Angeles",
        mls_config_ref="secret:mls-home-finder-config",
        transaction_platform_config_ref="secret:transaction-platform-home-finder",
        notification_settings={"telegram": True, "critical_failures": True},
        is_active=True,
        notes="Buyer-side investor work. Nevada license B.0146854 expires 2027-07-31. Office: 9890 S Maryland Pkwy Ste 200A.",
    )
    db.add(realtor)
    db.flush()
    return realtor


def seed_pirates_ig(db: Session, realtor: Realtor | None = None) -> Investor:
    """Client buy box from Pirates_IG_LLC_AI_Acquisition_Criteria.numbers."""
    realtor = realtor or seed_realtor(db)
    investor = (
        db.query(Investor)
        .filter(Investor.realtor_id == realtor.id, Investor.name == "Pirates IG LLC")
        .one_or_none()
    )
    if investor is None:
        investor = Investor(
            public_id=next_public_id(db, "INV"),
            realtor_id=realtor.id,
            name="Pirates IG LLC",
            contact_name="Amos",
            phone="+13109865887",
            email="rocky12345@yahoo.com",
            preferred_channel="sms",
            is_active=True,
            communication_permissions={"sms": False, "email": False},
            notes=(
                "Amos represents himself and a group of investors; he is the point of contact; "
                "additional investors may participate. SMS and email not confirmed — do not text "
                "or email until Damian confirms."
            ),
            import_source="Pirates_IG_LLC_AI_Acquisition_Criteria.numbers",
        )
        db.add(investor)
        db.flush()
    profile = (
        db.query(InvestorCriteria)
        .filter(
            InvestorCriteria.investor_id == investor.id,
            InvestorCriteria.name == "Pirates IG LLC acquisition",
        )
        .one_or_none()
    )
    if profile is None:
        profile = InvestorCriteria(
            public_id=next_public_id(db, "CRT"),
            realtor_id=realtor.id,
            investor_id=investor.id,
            name="Pirates IG LLC acquisition",
            is_active=True,
            geographic_area="Las Vegas; North Las Vegas; Henderson",
            cities=list(PIRATES_CITIES),
            property_types=["single_family"],
            hoa_required=False,
            max_price_pct_of_arv=PIRATES_MAX_PRICE_PCT_OF_ARV,
            preferred_financing="cash",
            occupancy_statuses=[],
            strict_fields=list(PIRATES_IG_STRICT_FIELDS),
            notes=(
                "Confirmed: SFH only; no HOA; cities LV/NLV/Henderson; max purchase 90% of ARV "
                "(10% below ARV); no dollar cap; no min beds/baths/sqft/year; all cash. "
                "Not confirmed: who supplies ARV, occupancy. Do not invent ARV."
            ),
            nl_criteria=(
                "A property qualifies only if it is a single-family home in Las Vegas, "
                "North Las Vegas, or Henderson, has no HOA, and can be purchased for 90% or less of ARV."
            ),
        )
        db.add(profile)
        db.flush()
        AuditService(db).record(
            event="CLIENT_PROFILE_SEEDED",
            object_type="investor",
            object_id=investor.public_id,
            actor="seed",
            actor_type=ActorType.SYSTEM.value,
            origin=ActorOrigin.AUTOMATION.value,
            realtor_id=str(realtor.id),
            after_state={"max_price_pct_of_arv": 0.90, "cities": list(PIRATES_CITIES)},
        )
    return investor
