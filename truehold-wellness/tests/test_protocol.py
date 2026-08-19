from wellness_agent.catalog import find_product, pdf_path, products
from wellness_agent.inventory.protocol import (
    PROTOCOLS,
    mg_per_ml,
    ml_for_units,
    units_for_dose_mg,
    verify_protocols,
)


def test_locked_tirzepatide_and_nad_math():
    tirz = PROTOCOLS["tirzepatide"]
    assert tirz["vial_mg"] == 20
    assert tirz["bac_ml"] == 2.0
    assert tirz["mg_per_ml"] == 10
    assert [step["units"] for step in tirz["steps"]] == [25, 50, 75, 100]
    assert tirz["steps"][0]["mg"] == 2.5
    assert tirz["steps"][0]["ml"] == 0.25
    assert tirz["steps"][0]["half_ml"] is True
    assert tirz["steps"][2]["half_ml"] is False
    nad = PROTOCOLS["nad"]
    assert nad["vial_mg"] == 1000
    assert nad["bac_ml"] == 5.0
    assert nad["steps"][0]["units"] == 50
    assert nad["steps"][0]["mg"] == 100
    assert nad["steps"][0]["ml"] == 0.5


def test_every_protocol_matches_stock_vial_and_unit_math():
    verify_protocols()
    stock_mg = {
        "tirzepatide": 20,
        "retatrutide": 20,
        "semax": 10,
        "nad": 1000,
        "klow": 80,
        "mots-c": 20,
        "ss-31": 10,
        "ghk-cu": 100,
    }
    catalog = {item["id"]: item for item in products()}
    for sku, spec in PROTOCOLS.items():
        assert sku in catalog
        assert str(stock_mg[sku]) in catalog[sku]["vial"]
        assert spec["vial_mg"] == stock_mg[sku]
        start = spec["steps"][0]
        assert start["half_ml"] is True
        recomputed = units_for_dose_mg(start["mg"], spec["vial_mg"], spec["bac_ml"])
        assert abs(recomputed - start["units"]) < 0.05
        assert abs(ml_for_units(start["units"]) - start["ml"]) < 1e-9
        assert abs(mg_per_ml(spec["vial_mg"], spec["bac_ml"]) * start["ml"] - start["mg"]) < 1e-6


def test_klow_10_units_is_four_mg_total_blend():
    spec = PROTOCOLS["klow"]
    assert spec["steps"][0]["units"] == 10
    assert spec["steps"][0]["mg"] == 4.0


def test_retatrutide_start_is_two_mg_weekly():
    spec = PROTOCOLS["retatrutide"]
    assert spec["steps"][0]["units"] == 20
    assert spec["steps"][0]["mg"] == 2.0


def test_semax_six_units_is_300_mcg():
    spec = PROTOCOLS["semax"]
    assert spec["steps"][0]["units"] == 6
    assert abs(spec["steps"][0]["mg"] - 0.3) < 1e-9
