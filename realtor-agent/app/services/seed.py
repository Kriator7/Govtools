from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import ActorOrigin, ActorType
from app.models.investor import Investor
from app.models.investor_criteria import PIRATES_IG_STRICT_FIELDS, InvestorCriteria
from app.models.realtor import Realtor
from app.services.audit import AuditService
from app.services.matching.screening import PIRATES_CITIES, PIRATES_MAX_PRICE_PCT_OF_ARV
from app.utilities.ids import next_public_id

TEST_REALTOR_NAME = "Test Operator"
TEST_INVESTOR_NAME = "Pirates IG LLC"
MOCK_SMS_NUMBER = "+15555550100"


def seed_realtor(db: Session) -> Realtor:
    """Seed the testing operator. Damian is not loaded until testing is confirmed."""
    settings = get_settings()
    existing = db.query(Realtor).filter(Realtor.is_active.is_(True)).order_by(Realtor.created_at.asc()).first()
    if existing:
        _apply_test_realtor(existing, settings)
        db.flush()
        return existing
    realtor = Realtor(
        public_id=next_public_id(db, "RLT"),
        name=TEST_REALTOR_NAME,
        brokerage="Test Brokerage",
        license_number="TEST-0001",
        license_state="NV",
        phone=settings.sms_relay_to,
        email=settings.email_from,
        telegram_chat_id=settings.telegram_operator_chat_id or "mock-realtor",
        timezone="America/Los_Angeles",
        mls_config_ref="secret:mls-test-config",
        transaction_platform_config_ref="secret:transaction-platform-test",
        notification_settings={"telegram": True, "email": True, "sms": True, "critical_failures": True},
        is_active=True,
        notes=(
            "Testing operator only. Outbound email uses EMAIL_FROM / EMAIL_RELAY_TO "
            f"({settings.email_from}). Damian Einbinder / Home Finder Realty will be added after testing."
        ),
    )
    db.add(realtor)
    db.flush()
    return realtor


def _apply_test_realtor(realtor: Realtor, settings) -> None:
    realtor.name = TEST_REALTOR_NAME
    realtor.brokerage = "Test Brokerage"
    realtor.license_number = "TEST-0001"
    realtor.email = settings.email_from
    realtor.phone = settings.sms_relay_to or realtor.phone
    if settings.telegram_operator_chat_id:
        realtor.telegram_chat_id = settings.telegram_operator_chat_id
    realtor.notes = (
        "Testing operator only. Damian Einbinder is not active in this environment yet. "
        f"Email relay: {settings.email_from}."
    )


def seed_pirates_ig(db: Session, realtor: Realtor | None = None) -> Investor:
    """Load the Numbers workbook as a **test template**, not live client traffic."""
    settings = get_settings()
    realtor = realtor or seed_realtor(db)
    test_phone = settings.sms_relay_to or (MOCK_SMS_NUMBER if settings.sms_provider == "mock" else None)
    investor = (
        db.query(Investor)
        .filter(Investor.realtor_id == realtor.id, Investor.name == TEST_INVESTOR_NAME)
        .one_or_none()
    )
    notes = (
        "TEST TEMPLATE from Pirates_IG_LLC_AI_Acquisition_Criteria.numbers. "
        "Not live Damian/Amos traffic. Preferred channel is SMS (Damian's stated preference). "
        "Live Twilio still relays to SMS_RELAY_TO; email copies go to "
        f"{settings.email_relay_to} while EMAIL_RELAY_MODE/NOTIFY_EMAIL_COPY are on."
    )
    if investor is None:
        investor = Investor(
            public_id=next_public_id(db, "INV"),
            realtor_id=realtor.id,
            name=TEST_INVESTOR_NAME,
            contact_name="Test Contact",
            phone=test_phone,
            email=settings.email_from,
            preferred_channel="sms",
            is_active=True,
            communication_permissions={"sms": True, "email": True},
            notes=notes,
            import_source="test-template:Pirates_IG_LLC_AI_Acquisition_Criteria.numbers",
        )
        db.add(investor)
        db.flush()
    else:
        investor.contact_name = "Test Contact"
        investor.phone = test_phone
        investor.email = settings.email_from
        investor.preferred_channel = "sms"
        investor.communication_permissions = {"sms": True, "email": True}
        investor.notes = notes
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
                "TEST TEMPLATE rules: SFH only; no HOA; LV/NLV/Henderson; max purchase 90% of ARV; "
                "no dollar cap; no min beds/baths/sqft/year; all cash. Do not invent ARV."
            ),
            nl_criteria=(
                "A property qualifies only if it is a single-family home in Las Vegas, "
                "North Las Vegas, or Henderson, has no HOA, and can be purchased for 90% or less of ARV."
            ),
        )
        db.add(profile)
        db.flush()
        AuditService(db).record(
            event="TEST_TEMPLATE_SEEDED",
            object_type="investor",
            object_id=investor.public_id,
            actor="seed",
            actor_type=ActorType.SYSTEM.value,
            origin=ActorOrigin.AUTOMATION.value,
            realtor_id=str(realtor.id),
            after_state={
                "max_price_pct_of_arv": 0.90,
                "cities": list(PIRATES_CITIES),
                "email_from": settings.email_from,
                "email_relay_to": settings.email_relay_to,
                "preferred_channel": "sms",
            },
        )
    return investor
