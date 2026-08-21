from decimal import Decimal

from app.integrations.telegram.mock import MockTelegramProvider
from app.models.enums import OpportunityStatus
from app.models.investor import Investor
from app.models.investor_criteria import InvestorCriteria
from app.models.listing import Listing
from app.models.opportunity import Opportunity
from app.services.criteria.telegram_apply import STRETCH_PROFILE_NAME, TelegramCriteriaService
from app.services.importing import InvestorImportService
from app.services.seed import DAMIAN_NAME, upsert_damian_realtor
from app.services.telegram.inbound import process_telegram_update
from app.services.telegram.notes import parse_realtor_note
from app.utilities.ids import next_public_id

DAMIAN_PRICE_NOTE = (
    "It should be 300k min let's go 600,000 max. Ideally, these are going to be rentals "
    "that will be held for a long time. This is not for flipping, etc. buy and hold."
)
DAMIAN_STRETCH_NOTE = (
    "I'm not saying that it's something more expensive that's a very good deal will not "
    "be looked at, but it's going to fall within different parameters"
)


def test_parse_damian_price_and_hold_note():
    parsed = parse_realtor_note(DAMIAN_PRICE_NOTE)
    assert parsed["min_price"] == Decimal("300000")
    assert parsed["max_price"] == Decimal("600000")
    assert parsed["buy_and_hold"] is True
    assert parsed["has_criteria"] is True


def test_parse_damian_stretch_note():
    parsed = parse_realtor_note(DAMIAN_STRETCH_NOTE)
    assert parsed["stretch_over_max"] is True
    assert parsed["has_criteria"] is True


def test_apply_damian_notes_updates_abc_and_rejects_summit_ridge(db, realtor, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.criteria.telegram_apply.NOTES_PATH", tmp_path / "notes.jsonl")
    from app.config import PROJECT_ROOT

    InvestorImportService(db).import_path(realtor, PROJECT_ROOT / "data" / "imports" / "sample_investors.csv")
    abc = db.query(Investor).filter(Investor.name == "ABC Capital").one()
    mf = (
        db.query(InvestorCriteria)
        .filter(InvestorCriteria.investor_id == abc.id, InvestorCriteria.name.contains("multifamily"))
        .one()
    )
    listing = Listing(
        public_id=next_public_id(db, "LST"),
        realtor_id=realtor.id,
        mls_listing_id="NV88888",
        street_address="88 Summit Ridge Court",
        city="Henderson",
        state="NV",
        zip_code="89052",
        asking_price=Decimal("875000"),
        arv=Decimal("950000"),
        property_type="multi_family",
        bedrooms=6,
        bathrooms=4,
        sqft=3200,
        year_built=1998,
        hoa_monthly=Decimal("0"),
    )
    db.add(listing)
    db.flush()
    opportunity = Opportunity(
        public_id=next_public_id(db, "OPP"),
        realtor_id=realtor.id,
        listing_id=listing.id,
        investor_id=abc.id,
        criteria_id=mf.id,
        score=100,
        score_category="excellent",
        explanation={},
        status=OpportunityStatus.AWAITING_REALTOR_REVIEW.value,
    )
    db.add(opportunity)
    db.flush()
    upsert_damian_realtor(db, {"name": DAMIAN_NAME})
    TelegramCriteriaService(db).remember_opportunity(realtor, opportunity.public_id)
    result = TelegramCriteriaService(db).apply_note(
        realtor,
        f"{DAMIAN_PRICE_NOTE} {DAMIAN_STRETCH_NOTE}",
        from_user={"username": "damianlasvegas", "id": "7592412078"},
    )
    assert result["ok"] is True
    db.refresh(mf)
    db.refresh(opportunity)
    assert mf.min_price == Decimal("300000")
    assert mf.max_price == Decimal("600000")
    assert "buy-and-hold" in (mf.name or "").lower() or "buy-and-hold" in (mf.notes or "").lower()
    assert opportunity.status == OpportunityStatus.REJECTED.value
    stretch = (
        db.query(InvestorCriteria)
        .filter(InvestorCriteria.investor_id == abc.id, InvestorCriteria.name == STRETCH_PROFILE_NAME)
        .one()
    )
    assert stretch.min_price == Decimal("600000")
    assert stretch.max_price_pct_of_arv == Decimal("0.9000")
    assert "300,000" in result["reply"]
    assert "600,000" in result["reply"]


def test_damian_group_text_updates_buy_box(db, realtor, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.criteria.telegram_apply.NOTES_PATH", tmp_path / "notes.jsonl")
    from app.config import PROJECT_ROOT

    InvestorImportService(db).import_path(realtor, PROJECT_ROOT / "data" / "imports" / "sample_investors.csv")
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "message": {
                "text": DAMIAN_PRICE_NOTE,
                "chat": {"id": -5372586958, "type": "group"},
                "from": {"id": 7592412078, "username": "damianlasvegas"},
            }
        },
        telegram=telegram,
    )
    assert result["action"] == "damian_note"
    abc = db.query(Investor).filter(Investor.name == "ABC Capital").one()
    sfh = (
        db.query(InvestorCriteria)
        .filter(InvestorCriteria.investor_id == abc.id, InvestorCriteria.name.contains("single-family"))
        .one()
    )
    assert sfh.min_price == Decimal("300000")
    assert sfh.max_price == Decimal("600000")
    assert "Got it" in telegram.sent[0]["text"]


def test_parse_condos_25_pct_arv():
    parsed = parse_realtor_note("Condos 25% arv")
    assert parsed["property_types"] == ["condo"]
    assert parsed["max_price_pct_of_arv"] == Decimal("0.2500")
    assert parsed["has_criteria"] is True
    assert parsed["min_price"] is None
    assert parsed["max_price"] is None


def test_apply_condo_arv_keeps_sfh_box_and_does_not_post_mock_cards(db, realtor, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.criteria.telegram_apply.NOTES_PATH", tmp_path / "notes.jsonl")
    from app.config import PROJECT_ROOT
    from app.services.matching.engine import MatchingEngine
    from app.services.seed import seed_pirates_ig

    InvestorImportService(db).import_path(realtor, PROJECT_ROOT / "data" / "imports" / "sample_investors.csv")
    pirates = seed_pirates_ig(db, realtor)
    upsert_damian_realtor(db, {"name": DAMIAN_NAME})
    TelegramCriteriaService(db).apply_note(
        realtor,
        DAMIAN_PRICE_NOTE,
        from_user={"username": "damianlasvegas", "id": "7592412078"},
    )
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "message": {
                "text": "Condos 25% arv",
                "chat": {"id": -5372586958, "type": "group"},
                "from": {"id": 7592412078, "username": "damianlasvegas"},
            }
        },
        telegram=telegram,
    )
    assert result["action"] == "damian_note"
    abc = db.query(Investor).filter(Investor.name == "ABC Capital").one()
    sfh = (
        db.query(InvestorCriteria)
        .filter(InvestorCriteria.investor_id == abc.id, InvestorCriteria.name.contains("single-family"))
        .one()
    )
    assert sfh.min_price == Decimal("300000")
    assert sfh.max_price == Decimal("600000")
    condo = (
        db.query(InvestorCriteria)
        .filter(InvestorCriteria.investor_id == abc.id, InvestorCriteria.name == "Telegram condo")
        .one()
    )
    assert condo.property_types == ["condo"]
    assert condo.max_price_pct_of_arv == Decimal("0.2500")
    assert condo.hoa_required is None
    pirates_box = (
        db.query(InvestorCriteria)
        .filter(InvestorCriteria.investor_id == pirates.id)
        .one()
    )
    assert pirates_box.property_types == ["single_family"]
    assert pirates_box.max_price_pct_of_arv == Decimal("0.9000")
    reply = telegram.sent[0]["text"]
    assert "Got it" in reply
    assert "condo" in reply.lower()
    assert "25%" in reply
    assert "I'll search MLS" in reply
    assert "not connected" in reply.lower()
    assert "Trestle" in reply
    assert not any("NEW INVESTOR MATCH" in (item.get("text") or "") for item in telegram.sent)
    pass_listing = Listing(
        public_id=next_public_id(db, "LST"),
        realtor_id=realtor.id,
        mls_listing_id="NVCONDO25",
        street_address="2210 Sahara Avenue Unit 412",
        city="Las Vegas",
        state="NV",
        zip_code="89104",
        asking_price=Decimal("75000"),
        arv=Decimal("320000"),
        property_type="condo",
        bedrooms=2,
        bathrooms=2,
        sqft=980,
        hoa_monthly=Decimal("245"),
    )
    fail_listing = Listing(
        public_id=next_public_id(db, "LST"),
        realtor_id=realtor.id,
        mls_listing_id="NVCONDO56",
        street_address="900 Las Vegas Boulevard Unit 18",
        city="Las Vegas",
        state="NV",
        zip_code="89101",
        asking_price=Decimal("180000"),
        arv=Decimal("320000"),
        property_type="condo",
        bedrooms=2,
        bathrooms=2,
        sqft=1100,
        hoa_monthly=Decimal("310"),
    )
    engine = MatchingEngine()
    assert engine.evaluate(pass_listing, condo).matched is True
    assert engine.evaluate(fail_listing, condo).matched is False
