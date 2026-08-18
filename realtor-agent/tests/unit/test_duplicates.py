from types import SimpleNamespace

from app.services.matching.duplicates import is_material_change, listing_fingerprint


def _listing(**overrides):
    data = dict(
        asking_price=425000,
        listing_status="active",
        seller_financing=False,
        foreclosure=False,
        short_sale=False,
        assumable_loan=False,
        occupancy_status="vacant",
        hoa_monthly=0,
        estimated_rent=2400,
        arv=None,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _snapshot(listing) -> dict:
    return {
        "asking_price": listing.asking_price,
        "listing_status": listing.listing_status,
        "seller_financing": listing.seller_financing,
        "foreclosure": listing.foreclosure,
        "short_sale": listing.short_sale,
        "assumable_loan": listing.assumable_loan,
        "occupancy_status": listing.occupancy_status,
        "hoa_monthly": listing.hoa_monthly,
        "estimated_rent": listing.estimated_rent,
        "arv": listing.arv,
    }


def test_same_material_fields_are_not_a_change():
    listing = _listing()
    assert listing_fingerprint(listing)
    assert not is_material_change(_snapshot(listing), listing)


def test_price_reduction_is_material():
    listing = _listing(asking_price=400000)
    previous = _listing(asking_price=425000)
    assert is_material_change(_snapshot(previous), listing)
