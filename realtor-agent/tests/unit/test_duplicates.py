from types import SimpleNamespace

from app.services.matching.duplicates import is_material_change, listing_fingerprint


def test_same_material_fields_are_not_a_change():
    listing = SimpleNamespace(
        asking_price=425000,
        listing_status="active",
        seller_financing=False,
        foreclosure=False,
        short_sale=False,
        assumable_loan=False,
        occupancy_status="vacant",
        hoa_monthly=0,
        estimated_rent=2400,
    )
    snapshot = {
        "asking_price": 425000,
        "listing_status": "active",
        "seller_financing": False,
        "foreclosure": False,
        "short_sale": False,
        "assumable_loan": False,
        "occupancy_status": "vacant",
        "hoa_monthly": 0,
        "estimated_rent": 2400,
    }
    assert listing_fingerprint(listing)
    assert not is_material_change(snapshot, listing)


def test_price_reduction_is_material():
    listing = SimpleNamespace(
        asking_price=400000,
        listing_status="active",
        seller_financing=False,
        foreclosure=False,
        short_sale=False,
        assumable_loan=False,
        occupancy_status="vacant",
        hoa_monthly=0,
        estimated_rent=2400,
    )
    snapshot = {
        "asking_price": 425000,
        "listing_status": "active",
        "seller_financing": False,
        "foreclosure": False,
        "short_sale": False,
        "assumable_loan": False,
        "occupancy_status": "vacant",
        "hoa_monthly": 0,
        "estimated_rent": 2400,
    }
    assert is_material_change(snapshot, listing)
