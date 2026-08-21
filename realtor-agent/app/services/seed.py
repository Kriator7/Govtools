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
DAMIAN_NAME = "Damian Einbinder"
DAMIAN_BROKERAGE = "Home Finder Realty"
DAMIAN_EMAIL = "binder@thehomefinderlv.com"
DAMIAN_TELEGRAM_USERNAMES = frozenset({"damianlasvegas"})


def seed_realtor(db: Session) -> Realtor:
    """Seed the testing operator. Never overwrite Damian's live packet record."""
    settings = get_settings()
    existing = db.query(Realtor).filter(Realtor.name == TEST_REALTOR_NAME).order_by(Realtor.created_at.asc()).first()
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


def find_damian_realtor(db: Session) -> Realtor | None:
    return (
        db.query(Realtor)
        .filter(Realtor.name.ilike("%Einbinder%"))
        .order_by(Realtor.created_at.asc())
        .first()
    )


def is_damian_telegram_user(user: dict | None) -> bool:
    """Match Damian's public Telegram username only. Do not SMS this user."""
    username = str((user or {}).get("username") or "").lstrip("@").lower()
    return username in DAMIAN_TELEGRAM_USERNAMES


def link_operator_group_chat(db: Session, chat_id: str | None = None) -> str | None:
    """Point Test Operator (and Damian if present) at the PirateEye group.

    Listing cards post to this chat. SMS/email relays stay on.
    """
    settings = get_settings()
    chat_id = (chat_id or settings.telegram_operator_chat_id or "").strip() or None
    if not chat_id:
        return None
    test = seed_realtor(db)
    test.telegram_chat_id = chat_id
    damian = find_damian_realtor(db)
    if damian is not None:
        damian.telegram_chat_id = chat_id
    db.flush()
    return chat_id


def link_damian_telegram(db: Session, user: dict | None, chat_id: str | None = None) -> Realtor | None:
    """Record Damian's Telegram user on his realtor row. Never overwrite Test Operator."""
    if not is_damian_telegram_user(user):
        return None
    damian = find_damian_realtor(db)
    if damian is None:
        return None
    user = user or {}
    user_id = str(user.get("id") or "").strip()
    username = str(user.get("username") or "").lstrip("@")
    if user_id:
        damian.telegram_user_id = user_id
    settings = dict(damian.notification_settings or {})
    if username:
        settings["telegram_username"] = username
        damian.notification_settings = settings
    if chat_id:
        damian.telegram_chat_id = str(chat_id)
    db.flush()
    return damian


def upsert_damian_realtor(db: Session, fields: dict | None = None) -> Realtor:
    """Create or update Damian from packet data only. Relays stay on."""
    fields = fields or {}
    realtor = find_damian_realtor(db)
    if realtor is None:
        realtor = (
            db.query(Realtor)
            .filter(Realtor.email == (fields.get("email") or DAMIAN_EMAIL))
            .one_or_none()
        )
        if realtor is not None and realtor.name == TEST_REALTOR_NAME:
            realtor = None
    if realtor is None:
        realtor = Realtor(
            public_id=next_public_id(db, "RLT"),
            name=fields.get("name") or DAMIAN_NAME,
            brokerage=fields.get("brokerage") or DAMIAN_BROKERAGE,
            email=fields.get("email") or DAMIAN_EMAIL,
            license_state="NV",
            timezone=fields.get("timezone") or "America/Los_Angeles",
            notification_settings={"telegram": True, "email": True, "sms": True, "critical_failures": True},
            is_active=True,
            notes="Live realtor record filled from Damian packet replies. SMS/email relays stay on.",
        )
        db.add(realtor)
        db.flush()
    _apply_damian_fields(realtor, fields)
    db.flush()
    return realtor


def _apply_damian_fields(realtor: Realtor, fields: dict) -> None:
    mapping = {
        "name": "name",
        "brokerage": "brokerage",
        "license_number": "license_number",
        "phone": "phone",
        "email": "email",
        "timezone": "timezone",
        "telegram_user_id": "telegram_user_id",
        "telegram_chat_id": "telegram_chat_id",
    }
    for source, attr in mapping.items():
        value = fields.get(source)
        if value:
            setattr(realtor, attr, value)
    extra = []
    for key in ("license_expiration", "broker_name", "broker_license", "office_address", "side"):
        if fields.get(key):
            extra.append(f"{key}: {fields[key]}")
    if extra:
        note = "Packet 1 fields: " + "; ".join(extra)
        existing = realtor.notes or ""
        if note not in existing:
            realtor.notes = f"{existing}\n{note}".strip()
    realtor.license_state = realtor.license_state or "NV"
    if not realtor.email:
        realtor.email = DAMIAN_EMAIL
    username = fields.get("telegram_username")
    if username:
        settings = dict(realtor.notification_settings or {})
        settings["telegram_username"] = str(username).lstrip("@")
        realtor.notification_settings = settings
