from pathlib import Path

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
