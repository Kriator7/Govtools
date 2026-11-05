from wellness_agent.cli import main
from wellness_agent.inventory.lots import (
    KLOW_VIALS_PER_KIT,
    RETATRUTIDE_VIALS_PER_KIT,
    TIRZEPATIDE_VIALS_PER_KIT,
    find_coa,
    find_lot,
    format_lots,
    load_packaged_lots,
    lot_id_for,
    receive_lot,
)
from wellness_agent.stock import load_stock, receive_stock, set_on_hand


def test_klow_five_kits_are_fifty_vials():
    assert 5 * KLOW_VIALS_PER_KIT == 50


def test_retatrutide_one_kit_is_ten_vials():
    assert 1 * RETATRUTIDE_VIALS_PER_KIT == 10


def test_tirzepatide_five_kits_are_fifty_vials():
    assert 5 * TIRZEPATIDE_VIALS_PER_KIT == 50


def test_packaged_klow_receipt_keeps_coa():
    data = load_packaged_lots()
    lots = [row for row in data["lots"] if row.get("sku_id") == "klow"]
    assert lots
    lot = lots[0]
    assert lot["kits_received"] == 5
    assert lot["vials_received"] == 50
    assert lot["label_code"] == "LUMI593-A62"
    assert lot["label_lot"] == "LOT-Z51-Z12"
    assert lot["coa_lot"] == "CPC260728KLOW"
    coa = next(row for row in data["coas"] if row.get("coa_id") == "CPC260728KLOW")
    assert coa["accession"] == "2607300355"
    assert coa["purity_percent"] == 99.88
    assert lot["lot_id"] in coa["associated_lot_ids"]
    from pathlib import Path
    from wellness_agent.inventory.lots import COA_DIR

    assert (COA_DIR / "CPC260728KLOW-Freedom-Diagnostics.jpg").is_file()
    assert (COA_DIR / "CPC260728KLOW-kits.jpg").is_file()
    tracker = data.get("tracker") or {}
    assert "drive.google.com/drive/folders/" in tracker.get("drive_folder", "")
    assert "docs.google.com/spreadsheets/" in tracker.get("lots_sheet", "")
    assert "docs.google.com/spreadsheets/" in tracker.get("coa_sheet", "")


def test_packaged_retatrutide_receipt_keeps_coa():
    data = load_packaged_lots()
    lots = [row for row in data["lots"] if row.get("sku_id") == "retatrutide"]
    assert lots
    lot = next(row for row in lots if row.get("kit_code") == "RT30")
    assert lot["kits_received"] == 1
    assert lot["vials_received"] == 10
    assert lot["vials_per_kit"] == 10
    assert lot["kit_code"] == "RT30"
    assert lot["label_code"] == "LUMI593-A20"
    assert lot["strength"] == "30 mg lyophilized vial"
    assert lot["coa_lot"] == "LOT-Z51-Z12"
    assert lot["coa_id"] == "COA-2026-ZFHGR0"
    klow = next(row for row in data["lots"] if row.get("sku_id") == "klow")
    assert klow["lot_id"] != lot["lot_id"]
    coa = next(row for row in data["coas"] if row.get("coa_id") == "COA-2026-ZFHGR0")
    assert coa["lab"] == "ILS Labs"
    assert coa["purity_percent"] == 99.73
    assert coa["mass_mg"] == 31.38
    assert coa["search_code"] == "TEESK66G"
    assert lot["lot_id"] in coa["associated_lot_ids"]
    from wellness_agent.inventory.lots import COA_DIR

    assert (COA_DIR / "COA-2026-ZFHGR0-ILS-Labs.jpg").is_file()
    assert (COA_DIR / "COA-2026-ZFHGR0-kits.jpg").is_file()


def test_packaged_retatrutide_20mg_receipt_keeps_coa():
    data = load_packaged_lots()
    lots = [row for row in data["lots"] if row.get("sku_id") == "retatrutide"]
    rt20 = next(row for row in lots if row.get("kit_code") == "RT20")
    rt30 = next(row for row in lots if row.get("kit_code") == "RT30")
    assert rt20["lot_id"] != rt30["lot_id"]
    assert rt20["kits_received"] == 1
    assert rt20["vials_received"] == 10
    assert rt20["strength"] == "20 mg lyophilized vial"
    assert rt20["label_code"] == "LUMI593-A19"
    assert rt20["coa_lot"] == "Z51-Z12"
    assert rt20["coa_id"] == "2609049012"
    coa = next(row for row in data["coas"] if row.get("coa_id") == "2609049012")
    assert coa["lab"] == "Freedom Diagnostics"
    assert coa["client"] == "Zyphera Labs"
    assert coa["purity_percent"] == 99.91
    assert coa["mass_mg"] == 21.38
    assert coa["search_code"] == "Zyph2609049012"
    assert rt20["lot_id"] in coa["associated_lot_ids"]
    from wellness_agent.inventory.lots import COA_DIR

    assert (COA_DIR / "2609049012-Freedom-Diagnostics.jpg").is_file()
    assert (COA_DIR / "2609049012-kits.jpg").is_file()


def test_packaged_tirzepatide_receipt_keeps_coa():
    data = load_packaged_lots()
    lots = [row for row in data["lots"] if row.get("sku_id") == "tirzepatide"]
    assert lots
    lot = lots[0]
    assert lot["kits_received"] == 5
    assert lot["vials_received"] == 50
    assert lot["vials_per_kit"] == 10
    assert lot["kit_code"] == "TR20"
    assert lot["label_code"] == "LUMI593-A09"
    assert lot["strength"] == "20 mg lyophilized vial"
    assert lot["coa_lot"] == "CORV593-A09"
    assert lot["coa_id"] == "2609030237"
    assert lot["lot_id"] == "TIRZEPATIDE-CORV593-A09-TR20"
    coa = next(row for row in data["coas"] if row.get("coa_id") == "2609030237")
    assert coa["lab"] == "Freedom Diagnostics"
    assert coa["client"] == "Corvinus Research"
    assert coa["purity_percent"] == 99.96
    assert coa["search_code"] == "Corv2609030237"
    assert coa["fentanyl_free"] is True
    assert lot["lot_id"] in coa["associated_lot_ids"]
    from wellness_agent.inventory.lots import COA_DIR

    assert (COA_DIR / "2609030237-Freedom-Diagnostics.jpg").is_file()
    assert (COA_DIR / "2609030237-kits.jpg").is_file()


def test_receive_lot_records_kits_lots_and_coa(tmp_path):
    result = receive_lot(
        "klow",
        kits=5,
        vials=50,
        label_code="LUMI593-A62",
        label_lot="LOT-Z51-Z12",
        coa_lot="CPC260728KLOW",
        received_at="2026-11-04",
        notes="associate this COA with the five kits",
        coa={
            "coa_id": "CPC260728KLOW",
            "lab": "Freedom Diagnostics",
            "accession": "2607300355",
            "purity_percent": 99.88,
            "file": "wellness_agent/inventory/coa/CPC260728KLOW-Freedom-Diagnostics.jpg",
        },
    )
    assert result["ok"] is True
    assert result["duplicate"] is False
    lot = result["lot"]
    assert lot["kits_received"] == 5
    assert lot["vials_per_kit"] == 10
    assert lot["vials_received"] == 50
    assert lot["vials_on_hand"] == 50
    assert lot["label_code"] == "LUMI593-A62"
    assert lot["label_lot"] == "LOT-Z51-Z12"
    assert lot["coa_lot"] == "CPC260728KLOW"
    assert lot["coa_id"] == "CPC260728KLOW"
    assert load_stock()["products"]["klow"]["on_hand"] == 50
    stored = find_lot(lot["lot_id"])
    assert stored is not None
    coa = find_coa("CPC260728KLOW")
    assert coa is not None
    assert stored["lot_id"] in coa["associated_lot_ids"]
    assert "CPC260728KLOW" in format_lots()
    assert "LOT-Z51-Z12" in format_lots()


def test_receive_lot_retatrutide_defaults_to_ten_vial_kits():
    result = receive_lot(
        "retatrutide",
        kits=1,
        kit_code="RT30",
        strength="30 mg lyophilized vial",
        label_code="LUMI593-A20",
        coa_lot="LOT-Z51-Z12",
        received_at="2026-11-04",
        coa={
            "coa_id": "COA-2026-ZFHGR0",
            "lab": "ILS Labs",
            "purity_percent": 99.73,
            "mass_mg": 31.38,
        },
    )
    lot = result["lot"]
    assert lot["kits_received"] == 1
    assert lot["vials_received"] == 10
    assert lot["vials_per_kit"] == 10
    assert lot["strength"] == "30 mg lyophilized vial"
    assert lot["kit_code"] == "RT30"
    assert lot["coa_id"] == "COA-2026-ZFHGR0"
    assert load_stock()["products"]["retatrutide"]["on_hand"] == 10
    assert lot["lot_id"] == lot_id_for(
        sku_id="retatrutide", coa_lot="LOT-Z51-Z12", kit_code="RT30"
    )
    assert "RT30" in format_lots()
    assert "30 mg lyophilized vial" in format_lots()


def test_receive_lot_tirzepatide_five_kits_are_fifty_vials():
    result = receive_lot(
        "tirzepatide",
        kits=5,
        kit_code="TR20",
        strength="20 mg lyophilized vial",
        label_code="LUMI593-A09",
        coa_lot="CORV593-A09",
        received_at="2026-11-04",
        coa={
            "coa_id": "2609030237",
            "lab": "Freedom Diagnostics",
            "accession": "2609030237",
            "purity_percent": 99.96,
        },
    )
    lot = result["lot"]
    assert lot["kits_received"] == 5
    assert lot["vials_received"] == 50
    assert lot["vials_per_kit"] == 10
    assert lot["kit_code"] == "TR20"
    assert lot["coa_id"] == "2609030237"
    assert load_stock()["products"]["tirzepatide"]["on_hand"] == 50
    assert lot["lot_id"] == lot_id_for(
        sku_id="tirzepatide", coa_lot="CORV593-A09", kit_code="TR20"
    )


def test_format_stock_splits_mixed_retatrutide_strengths():
    from wellness_agent.stock import format_stock

    thirty = receive_lot(
        "retatrutide",
        kits=1,
        kit_code="RT30",
        strength="30 mg lyophilized vial",
        coa_lot="LOT-Z51-Z12",
        coa={"coa_id": "COA-2026-ZFHGR0"},
    )
    twenty = receive_lot(
        "retatrutide",
        kits=1,
        kit_code="RT20",
        strength="20 mg lyophilized vial",
        label_code="LUMI593-A19",
        coa_lot="Z51-Z12",
        coa={"coa_id": "2609049012"},
    )
    assert thirty["lot"]["lot_id"] != twenty["lot"]["lot_id"]
    text = format_stock()
    assert "20 mg lyophilized vial" in text
    assert "30 mg lyophilized vial" in text
    assert "20 on hand (20 mg lyophilized vial)" not in text
    lots_text = format_lots()
    assert "RT20" in lots_text
    assert "RT30" in lots_text


def test_receive_lot_is_idempotent():
    first = receive_lot("klow", kits=5, coa_lot="CPC260728KLOW", label_lot="LOT-Z51-Z12")
    second = receive_lot("klow", kits=5, coa_lot="CPC260728KLOW", label_lot="LOT-Z51-Z12")
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert load_stock()["products"]["klow"]["on_hand"] == 50


def test_receive_lot_rejects_kit_vial_mismatch():
    try:
        receive_lot("klow", kits=5, vials=40, coa_lot="CPC260728KLOW")
    except ValueError as exc:
        assert "not 40" in str(exc)
    else:
        raise AssertionError("expected kit/vial mismatch")


def test_receive_stock_starts_unset_at_zero():
    entry = receive_stock("semax", 3, reason="lot-receipt", detail="test")
    assert entry["previous"] is None
    assert entry["on_hand"] == 3
    set_on_hand("semax", 3)
    again = receive_stock("semax", 2, reason="lot-receipt", detail="more")
    assert again["previous"] == 3
    assert again["on_hand"] == 5


def test_receive_stock_cli(capsys):
    assert (
        main(
            [
                "receive-stock",
                "--sku",
                "klow",
                "--kits",
                "5",
                "--label-code",
                "LUMI593-A62",
                "--label-lot",
                "LOT-Z51-Z12",
                "--coa-lot",
                "CPC260728KLOW",
                "--received-at",
                "2026-11-04",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "5 kits" in out
    assert "50 vials" in out
    assert main(["lots"]) == 0
    lots_out = capsys.readouterr().out
    assert "KLOW" in lots_out
    assert "CPC260728KLOW" in lots_out
    assert lot_id_for(sku_id="klow", coa_lot="CPC260728KLOW", label_lot="LOT-Z51-Z12") in lots_out
