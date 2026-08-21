from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from app.config import PROJECT_ROOT
from app.models.investor import Investor
from app.models.investor_criteria import InvestorCriteria
from app.services.importing import InvestorImportService


def test_sample_csv_import(db, realtor):
    path = PROJECT_ROOT / "data" / "imports" / "sample_investors.csv"
    result = InvestorImportService(db).import_path(realtor, path)
    assert result["created_investors"] == 2
    assert result["created_profiles"] == 3
    assert result["errors"] == []
    abc = db.query(Investor).filter(Investor.name == "ABC Capital").one()
    profiles = db.query(InvestorCriteria).filter(InvestorCriteria.investor_id == abc.id).all()
    assert len(profiles) == 2
    names = {item.name for item in profiles}
    assert "Las Vegas single-family rentals" in names
    assert "Henderson multifamily value-add" in names


def test_invalid_row_is_reported(db, realtor, tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("Phone,Email\n+1555,nobody@example.invalid\n", encoding="utf-8")
    result = InvestorImportService(db).import_path(realtor, path)
    assert result["created_investors"] == 0
    assert result["errors"]
    assert "Investor Name is required" in result["errors"][0]["error"]


def test_xlsx_header_row_and_text_permission_no(db, realtor):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Current Investor Clientele"])
    sheet.append(["Do not text or email without consent"])
    sheet.append([])
    sheet.append(
        [
            "Investor Name",
            "Contact Name",
            "Phone",
            "Email",
            "Preferred Channel",
            "May we text?",
            "May we email?",
            "Buying Areas",
            "Property Type",
            "HOA",
            "Maximum Purchase Price (% ARV)",
            "Required ARV Discount",
            "Funding",
            "Assigned Notes",
        ]
    )
    sheet.append(
        [
            "Pirates IG LLC",
            "Amos",
            "+15555550199",
            "amos@example.test",
            "Phone call",
            "No",
            "No",
            "LV / NLV / Henderson",
            "SFH",
            "No HOA",
            0.9,
            0.1,
            "all cash",
            "all-cash; SMS/email consent not confirmed",
        ]
    )
    buffer = BytesIO()
    workbook.save(buffer)
    result = InvestorImportService(db).import_bytes(realtor, buffer.getvalue(), "clientele.xlsx")
    assert result["errors"] == []
    assert result["created_investors"] == 1
    investor = db.query(Investor).filter(Investor.name == "Pirates IG LLC").one()
    assert investor.preferred_channel == "phone"
    assert investor.communication_permissions == {"sms": False, "email": False}
    assert investor.phone == "+15555550199"
    profile = db.query(InvestorCriteria).filter(InvestorCriteria.investor_id == investor.id).one()
    assert profile.cities == ["Las Vegas", "North Las Vegas", "Henderson"]
    assert profile.property_types == ["single_family"]
    assert profile.hoa_required is False
    assert float(profile.max_price_pct_of_arv) == 0.9
    assert float(profile.min_desired_discount) == 0.1
    assert profile.preferred_financing == "cash"
