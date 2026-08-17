"""Acquisition profile. One investor may have many profiles (e.g. LV SFH vs Henderson MF)."""

from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import PublicIdMixin, RealtorScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

DEFAULT_STRICT_FIELDS = [
    "min_price",
    "max_price",
    "max_purchase_price",
    "zip_codes",
    "cities",
    "property_types",
    "min_bedrooms",
    "min_bathrooms",
]


class InvestorCriteria(UUIDPrimaryKeyMixin, PublicIdMixin, RealtorScopedMixin, TimestampMixin, Base):
    __tablename__ = "investor_criteria"

    investor_id = mapped_column(ForeignKey("investors.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="Default")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    min_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    geographic_area: Mapped[str | None] = mapped_column(String(200), nullable=True)
    zip_codes: Mapped[list] = mapped_column(JSON, default=list)
    cities: Mapped[list] = mapped_column(JSON, default=list)
    neighborhoods: Mapped[list] = mapped_column(JSON, default=list)

    property_types: Mapped[list] = mapped_column(JSON, default=list)
    min_bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_bathrooms: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    min_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_lot_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_built_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_built_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    hoa_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    max_hoa: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_dom: Mapped[int | None] = mapped_column(Integer, nullable=True)
    require_price_reduction: Mapped[bool] = mapped_column(Boolean, default=False)

    min_cap_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    min_estimated_rent: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_grm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    rehab_tolerance: Mapped[str | None] = mapped_column(String(80), nullable=True)
    occupancy_statuses: Mapped[list] = mapped_column(JSON, default=list)
    min_cash_flow: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_repair_estimate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    min_desired_equity: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    min_desired_discount: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)

    seller_financing_preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    foreclosure_preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    short_sale_preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    assumable_loan_preferred: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    exclusion_rules: Mapped[list] = mapped_column(JSON, default=list)
    strict_fields: Mapped[list] = mapped_column(JSON, default=lambda: list(DEFAULT_STRICT_FIELDS))
    nl_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)

    investor = relationship("Investor", back_populates="criteria_profiles")
    opportunities = relationship("Opportunity", back_populates="criteria")
