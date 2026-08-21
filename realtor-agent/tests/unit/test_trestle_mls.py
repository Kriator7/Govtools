from decimal import Decimal

from app.integrations.mls.trestle import TrestleMLSProvider
from app.services.providers import get_mls_provider


def test_get_mls_provider_stays_mock_without_credentials(monkeypatch):
    monkeypatch.setenv("MLS_PROVIDER", "trestle")
    monkeypatch.setenv("MLS_API_KEY", "")
    monkeypatch.setenv("MLS_CLIENT_ID", "")
    monkeypatch.setenv("MLS_CLIENT_SECRET", "")
    from app.config import get_settings

    get_settings.cache_clear()
    provider = get_mls_provider(get_settings())
    assert provider.name == "mock"


def test_trestle_normalizes_reso_property_and_does_not_invent_arv():
    provider = TrestleMLSProvider.__new__(TrestleMLSProvider)
    draft = TrestleMLSProvider.normalize_listing(
        provider,
        {
            "ListingId": "LV998877",
            "UnparsedAddress": "100 Main St",
            "City": "Las Vegas",
            "StateOrProvince": "NV",
            "PostalCode": "89101",
            "ListPrice": 425000,
            "PropertySubType": "Single Family Residence",
            "BedroomsTotal": 3,
            "StandardStatus": "Active",
        },
    )
    assert draft.mls_listing_id == "LV998877"
    assert draft.city == "Las Vegas"
    assert draft.asking_price == Decimal("425000")
    assert draft.arv is None
    assert draft.provider == "trestle"
