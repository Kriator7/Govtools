"""Investor spreadsheet import. Invalid rows are reported, never silently dropped."""

import csv
from io import BytesIO, StringIO
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.investor import Investor
from app.models.investor_criteria import DEFAULT_STRICT_FIELDS, InvestorCriteria
from app.models.realtor import Realtor
from app.services.audit import AuditService
from app.utilities.ids import next_public_id
from app.utilities.money import as_decimal
from app.utilities.parsing import as_float, as_int, first_present, split_list

COLUMN_ALIASES = {
    "name": ["investor name", "name", "company", "entity"],
    "contact_name": ["contact name", "contact", "primary contact"],
    "phone": ["phone", "mobile", "cell"],
    "email": ["email", "e-mail"],
    "channel": ["preferred channel", "channel", "preferred notification method"],
    "min_price": ["minimum price", "min price", "min_price"],
    "max_price": ["maximum price", "max price", "max_price"],
    "cities": ["cities", "city"],
    "zip_codes": ["zip codes", "zips", "zip", "zip code"],
    "property_types": ["property types", "property type", "types"],
    "bedrooms": ["bedrooms", "beds", "min bedrooms"],
    "bathrooms": ["bathrooms", "baths", "min bathrooms"],
    "min_sqft": ["minimum sq ft", "min sq ft", "min_sqft", "sqft"],
    "max_hoa": ["max hoa", "hoa", "max_hoa"],
    "financing": ["cash / finance", "financing", "cash/finance"],
    "notes": ["notes", "comments"],
    "profile_name": ["profile", "criteria profile", "profile name"],
    "year_built_min": ["year built min", "min year built", "year_built_min"],
}


class InvestorImportService:
    def __init__(self, db: Session, audit: AuditService | None = None) -> None:
        self.db = db
        self.audit = audit or AuditService(db)

    def import_path(self, realtor: Realtor, path: Path, source: str | None = None) -> dict:
        rows = _read_tabular(path)
        return self.import_rows(realtor, rows, source=source or path.name)

    def import_bytes(self, realtor: Realtor, data: bytes, filename: str) -> dict:
        suffix = Path(filename).suffix.lower()
        if suffix in {".xlsx", ".xlsm"}:
            rows = _read_xlsx(data)
        else:
            text = data.decode("utf-8-sig")
            rows = list(csv.DictReader(StringIO(text)))
        return self.import_rows(realtor, rows, source=filename)

    def import_rows(self, realtor: Realtor, rows: list[dict], source: str) -> dict:
        created_investors = 0
        created_profiles = 0
        errors: list[dict] = []
        for index, raw in enumerate(rows, start=2):
            if not any(str(v).strip() for v in raw.values() if v is not None):
                continue
            try:
                payload = _normalize_row(raw)
                investor = (
                    self.db.query(Investor)
                    .filter(Investor.realtor_id == realtor.id, Investor.name == payload["name"])
                    .one_or_none()
                )
                if investor is None:
                    investor = Investor(
                        public_id=next_public_id(self.db, "INV"),
                        realtor_id=realtor.id,
                        name=payload["name"],
                        contact_name=payload.get("contact_name"),
                        phone=payload.get("phone"),
                        email=payload.get("email"),
                        preferred_channel=payload.get("channel") or "sms",
                        notes=payload.get("notes"),
                        communication_permissions={"sms": True, "email": True},
                        import_source=source,
                    )
                    self.db.add(investor)
                    self.db.flush()
                    created_investors += 1
                criteria = InvestorCriteria(
                    public_id=next_public_id(self.db, "CRT"),
                    realtor_id=realtor.id,
                    investor_id=investor.id,
                    name=payload.get("profile_name") or "Imported profile",
                    min_price=payload.get("min_price"),
                    max_price=payload.get("max_price"),
                    cities=payload.get("cities") or [],
                    zip_codes=payload.get("zip_codes") or [],
                    property_types=payload.get("property_types") or [],
                    min_bedrooms=payload.get("bedrooms"),
                    min_bathrooms=payload.get("bathrooms"),
                    min_sqft=payload.get("min_sqft"),
                    max_hoa=payload.get("max_hoa"),
                    year_built_min=payload.get("year_built_min"),
                    notes=payload.get("notes"),
                    strict_fields=list(DEFAULT_STRICT_FIELDS),
                )
                self.db.add(criteria)
                self.db.flush()
                created_profiles += 1
            except Exception as exc:  # noqa: BLE001
                errors.append({"row": index, "error": str(exc), "data": {k: str(v) for k, v in raw.items()}})
        self.audit.record(
            event="INVESTORS_IMPORTED",
            object_type="investor_import",
            object_id=source,
            actor="import_service",
            realtor_id=str(realtor.id),
            after_state={
                "created_investors": created_investors,
                "created_profiles": created_profiles,
                "errors": len(errors),
            },
        )
        return {
            "created_investors": created_investors,
            "created_profiles": created_profiles,
            "errors": errors,
            "rows_processed": len(rows),
        }


def _normalize_row(raw: dict) -> dict:
    name = first_present(raw, COLUMN_ALIASES["name"])
    if not name:
        raise ValueError("Investor Name is required")
    channel = str(first_present(raw, COLUMN_ALIASES["channel"]) or "sms").strip().lower()
    if channel in {"text", "mobile"}:
        channel = "sms"
    types = [item.lower().replace(" ", "_") for item in split_list(first_present(raw, COLUMN_ALIASES["property_types"]))]
    return {
        "name": str(name).strip(),
        "contact_name": _str(first_present(raw, COLUMN_ALIASES["contact_name"])),
        "phone": _str(first_present(raw, COLUMN_ALIASES["phone"])),
        "email": _str(first_present(raw, COLUMN_ALIASES["email"])),
        "channel": channel,
        "min_price": as_decimal(first_present(raw, COLUMN_ALIASES["min_price"])),
        "max_price": as_decimal(first_present(raw, COLUMN_ALIASES["max_price"])),
        "cities": split_list(first_present(raw, COLUMN_ALIASES["cities"])),
        "zip_codes": split_list(first_present(raw, COLUMN_ALIASES["zip_codes"])),
        "property_types": types,
        "bedrooms": as_int(first_present(raw, COLUMN_ALIASES["bedrooms"])),
        "bathrooms": as_float(first_present(raw, COLUMN_ALIASES["bathrooms"])),
        "min_sqft": as_int(first_present(raw, COLUMN_ALIASES["min_sqft"])),
        "max_hoa": as_decimal(first_present(raw, COLUMN_ALIASES["max_hoa"])),
        "notes": _str(first_present(raw, COLUMN_ALIASES["notes"])),
        "profile_name": _str(first_present(raw, COLUMN_ALIASES["profile_name"])),
        "financing": _str(first_present(raw, COLUMN_ALIASES["financing"])),
        "year_built_min": as_int(first_present(raw, COLUMN_ALIASES["year_built_min"])),
    }


def _str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _read_tabular(path: Path) -> list[dict]:
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        return _read_xlsx(path.read_bytes())
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _read_xlsx(data: bytes) -> list[dict]:
    workbook = load_workbook(filename=BytesIO(data), read_only=True, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    result = []
    for row in rows[1:]:
        result.append({headers[i]: row[i] if i < len(row) else None for i in range(len(headers))})
    return result
