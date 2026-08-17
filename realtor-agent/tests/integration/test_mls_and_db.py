from app.integrations.mls.mock import MockMLSProvider
from app.models.listing import Listing
from app.services.mls.ingest import ListingIngestService


def test_mock_mls_normalizes_and_dedupes(db, realtor):
    provider = MockMLSProvider()
    assert provider.authenticate()
    service = ListingIngestService(db, provider)
    first = service.sync(realtor, incremental=False)
    second = service.sync(realtor, incremental=False)
    assert first["created"] >= 3
    assert second["created"] == 0
    count = db.query(Listing).filter(Listing.realtor_id == realtor.id).count()
    assert count == first["created"]
    listing = db.query(Listing).filter(Listing.mls_listing_id == "NV12345").one()
    assert listing.city == "Las Vegas"
    assert listing.raw_payload["mls_id"] == "NV12345"
