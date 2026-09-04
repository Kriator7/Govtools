from decimal import Decimal
from pathlib import Path

from app.integrations.open_leads.catalog import providers_for
from app.integrations.open_leads.market import assessor_search_url, obituary_rss_url
from app.integrations.open_leads.parse import asking_price_from_text, person_from_obituary_title, street_from_text
from app.integrations.open_leads.rss import parse_feed_items
from app.integrations.open_leads.rss_providers import RssOpenLeadProvider
from app.models.listing import Listing
from app.models.seller_lead import SellerLead
from app.services.open_leads.hunt import OpenLeadHuntService
from app.services.telegram.inbound import process_telegram_update
from app.integrations.telegram.mock import MockTelegramProvider

RSS_PATH = Path(__file__).parent / "fixtures" / "sample_open_leads.rss.xml"


def test_obituary_name_and_fsbo_price_parse():
    assert person_from_obituary_title("Maria Elena Cruz Obituary - Las Vegas, NV") == "Maria Elena Cruz"
    assert person_from_obituary_title("Obituary for John Alan Pike") == "John Alan Pike"
    assert asking_price_from_text("$285,000 / 3br") == Decimal("285000")
    assert street_from_text("4120 Desert Bloom Ave, Henderson") == "4120 Desert Bloom Ave"


def test_assessor_search_stays_public():
    url = assessor_search_url("Maria Elena Cruz")
    assert "clarkcountynv.gov" in url
    assert "Maria" in url or "maria" in url.lower() or "Cruz" in url


def test_rss_provider_marks_obituaries_review_only():
    xml = RSS_PATH.read_text(encoding="utf-8")
    provider = RssOpenLeadProvider(
        feed_url="https://example.invalid/rss",
        source="obituary",
        review_only=True,
        get_text=lambda _url: xml,
    )
    drafts = provider.search()
    assert drafts
    assert drafts[0].review_only is True
    assert drafts[0].person_name == "John Alan Pike"
    assert drafts[0].can_become_listing is False


def test_rss_provider_parses_fsbo_address():
    xml = RSS_PATH.read_text(encoding="utf-8")
    provider = RssOpenLeadProvider(
        feed_url="https://example.invalid/rss",
        source="fsbo",
        review_only=False,
        get_text=lambda _url: xml,
    )
    drafts = {item.url: item for item in provider.search()}
    fsbo = drafts["https://example.invalid/fsbo/rainbow"]
    assert fsbo.asking_price == Decimal("199000")
    assert fsbo.street_address
    assert "Rainbow" in fsbo.street_address
    assert fsbo.can_become_listing is True


def test_parse_feed_items_from_sample_rss():
    items = parse_feed_items(RSS_PATH.read_text(encoding="utf-8"))
    assert len(items) == 2
    assert "Pike" in items[0]["title"]


def test_fixture_hunt_stores_obituary_and_converts_fsbo(db, realtor, monkeypatch):
    monkeypatch.setenv("OPEN_LEADS_MODE", "fixture")
    from app.config import get_settings

    get_settings.cache_clear()
    result = OpenLeadHuntService(db).hunt(realtor, mode="fixture")
    db.commit()
    assert result["created"] == 4
    assert result["converted"] == 1
    leads = db.query(SellerLead).filter(SellerLead.realtor_id == realtor.id).all()
    obits = [row for row in leads if row.source == "obituary"]
    assert obits
    assert obits[0].review_only is True
    assert obits[0].listing_id is None
    fsbo = [row for row in leads if row.source == "fsbo"][0]
    assert fsbo.listing_id is not None
    listing = db.get(Listing, fsbo.listing_id)
    assert listing is not None
    assert listing.provider == "fsbo"
    assert listing.street_address.startswith("4120")


def test_telegram_hunt_posts_estate_watch_without_auto_contact(db, realtor, tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_LEADS_MODE", "fixture")
    from app.config import get_settings

    get_settings.cache_clear()
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {"message": {"text": "/hunt", "chat": {"id": 4242}, "from": {"id": 4242}}},
        telegram=telegram,
    )
    assert result["action"] == "hunt"
    assert result["created"] == 4
    blob = "\n".join(item["text"] for item in telegram.sent)
    assert "Obituary" in blob or "estate-watch" in blob.lower()
    assert "Do not auto-contact" in blob
    assert "Maria Elena Cruz" in blob
    assert "/hunt" not in blob or "PirateEye hunt" in blob
    keep = process_telegram_update(
        db,
        realtor,
        {
            "callback_query": {
                "id": "cb-keep",
                "data": f"lead:keep:{result['lead_ids'][0]}",
                "message": {"chat": {"id": 4242}},
            }
        },
        telegram=telegram,
    )
    assert keep["ok"] is True
    assert keep["action"] == "lead-keep"


def test_telegram_obits_and_help(db, realtor, tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_LEADS_MODE", "fixture")
    from app.config import get_settings

    get_settings.cache_clear()
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    help_result = process_telegram_update(
        db,
        realtor,
        {"message": {"text": "/help", "chat": {"id": 4242}, "from": {"id": 4242}}},
        telegram=telegram,
    )
    assert help_result["action"] == "help"
    assert "obituaries" in telegram.sent[0]["text"].lower()
    obits = process_telegram_update(
        db,
        realtor,
        {"message": {"text": "obituaries", "chat": {"id": 4242}, "from": {"id": 4242}}},
        telegram=telegram,
    )
    assert obits["action"] == "hunt"
    assert obits["source"] == "obituary"
    assert all(lead.startswith("LED-") for lead in obits["lead_ids"])


def test_google_news_obituary_url_is_public_rss():
    url = obituary_rss_url()
    assert url.startswith("https://news.google.com/rss/search")
    assert "obituary" in url.lower()


def test_providers_fixture_mode_filters_source(monkeypatch):
    monkeypatch.setenv("OPEN_LEADS_MODE", "fixture")
    from app.config import get_settings

    get_settings.cache_clear()
    rows = providers_for("obituary", mode="fixture")
    assert len(rows) == 1
    drafts = rows[0].search()
    assert drafts and all(item.source == "obituary" for item in drafts)
    assert all(item.review_only for item in drafts)
