from decimal import Decimal
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import ORMModel


class InvestorCreate(ORMModel):
    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    preferred_channel: str = "sms"
    is_active: bool = True
    notes: str | None = None
    communication_permissions: dict = Field(default_factory=lambda: {"sms": True, "email": True})


class InvestorUpdate(ORMModel):
    name: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    preferred_channel: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    communication_permissions: dict | None = None


class InvestorRead(InvestorCreate):
    id: UUID
    public_id: str
    realtor_id: UUID


class CriteriaCreate(ORMModel):
    name: str = "Default"
    is_active: bool = True
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    max_purchase_price: Decimal | None = None
    geographic_area: str | None = None
    zip_codes: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    neighborhoods: list[str] = Field(default_factory=list)
    property_types: list[str] = Field(default_factory=list)
    min_bedrooms: int | None = None
    min_bathrooms: float | None = None
    min_sqft: int | None = None
    max_sqft: int | None = None
    min_lot_sqft: int | None = None
    year_built_min: int | None = None
    year_built_max: int | None = None
    hoa_required: bool | None = None
    max_hoa: Decimal | None = None
    max_dom: int | None = None
    require_price_reduction: bool = False
    min_cap_rate: Decimal | None = None
    min_estimated_rent: Decimal | None = None
    max_grm: Decimal | None = None
    rehab_tolerance: str | None = None
    occupancy_statuses: list[str] = Field(default_factory=list)
    min_cash_flow: Decimal | None = None
    max_repair_estimate: Decimal | None = None
    min_desired_equity: Decimal | None = None
    min_desired_discount: Decimal | None = None
    max_price_pct_of_arv: Decimal | None = None
    preferred_financing: str | None = None
    seller_financing_preferred: bool = False
    foreclosure_preferred: bool = False
    short_sale_preferred: bool = False
    assumable_loan_preferred: bool = False
    notes: str | None = None
    exclusion_rules: list[dict] = Field(default_factory=list)
    strict_fields: list[str] | None = None
    nl_criteria: str | None = None


class CriteriaRead(CriteriaCreate):
    id: UUID
    public_id: str
    investor_id: UUID
    realtor_id: UUID


class InvestorImportResult(ORMModel):
    created_investors: int
    created_profiles: int
    errors: list[dict] = Field(default_factory=list)
    rows_processed: int
