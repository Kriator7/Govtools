from pathlib import Path

from app.services.documents.pdf import ensure_sample_template, fill_pdf
from app.services.documents.registry import TemplateRegistry


def test_field_map_keys(tmp_path: Path):
    registry = TemplateRegistry()
    spec = registry.get("purchase_agreement", "v1")
    assert spec.field_map["buyer_name"] == "BuyerFullName"
    assert spec.field_map["purchase_price"] == "PurchasePrice"
    assert "earnest_money" in spec.required_fields


def test_fill_does_not_modify_template(tmp_path: Path):
    template = tmp_path / "template.pdf"
    ensure_sample_template(template)
    original = template.read_bytes()
    filled = fill_pdf(
        template,
        {
            "BuyerFullName": "ABC Capital LLC",
            "PropertyAddress": "123 Main Street, Las Vegas, NV 89123",
            "PurchasePrice": "$425,000",
            "EarnestDeposit": "$5,000",
            "ClosingDate": "2026-09-30",
            "FinancingType": "cash",
        },
    )
    assert template.read_bytes() == original
    assert filled != original
    assert len(filled) > 0
