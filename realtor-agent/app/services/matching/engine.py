"""Deterministic matching of a normalized listing against investor criteria.

A strict miss rejects the match. A preferred miss lowers the score and is
explained as a potential issue. AI is not used for threshold decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.config import scoring_weights_defaults
from app.models.investor_criteria import DEFAULT_STRICT_FIELDS, InvestorCriteria
from app.models.listing import Listing
from app.services.scoring.engine import score_category, weighted_score
from app.utilities.money import money_label


@dataclass
class MatchResult:
    matched: bool
    score: Decimal
    category: str
    reasons: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    explanation: dict = field(default_factory=dict)

    def as_explanation(self, investor_name: str) -> dict:
        return {
            "match_score": float(self.score),
            "category": self.category,
            "investor": investor_name,
            "reasons": self.reasons,
            "potential_issues": self.issues,
            "failures": self.failures,
            "matched": self.matched,
        }


class MatchingEngine:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or scoring_weights_defaults()

    def evaluate(self, listing: Listing, criteria: InvestorCriteria) -> MatchResult:
        reasons: list[str] = []
        issues: list[str] = []
        failures: list[str] = []
        deductions: list[float] = []

        self._apply_exclusions(listing, criteria, failures)
        self._compare_price(listing, criteria, reasons, issues, failures, deductions)
        self._compare_geo(listing, criteria, reasons, issues, failures, deductions)
        self._compare_property_type(listing, criteria, reasons, issues, failures, deductions)
        self._compare_beds_baths(listing, criteria, reasons, issues, failures, deductions)
        self._compare_size(listing, criteria, reasons, issues, failures, deductions)
        self._compare_year(listing, criteria, reasons, issues, failures, deductions)
        self._compare_hoa(listing, criteria, reasons, issues, failures, deductions)
        self._compare_dom_and_reductions(listing, criteria, reasons, issues, failures, deductions)
        self._compare_financials(listing, criteria, reasons, issues, failures, deductions)
        self._compare_flags(listing, criteria, reasons, issues, deductions)

        score = weighted_score(deductions, self.weights)
        matched = not failures
        category = score_category(score) if matched else "rejected"
        result = MatchResult(
            matched=matched,
            score=score if matched else Decimal("0"),
            category=category,
            reasons=reasons,
            issues=issues,
            failures=failures,
        )
        result.explanation = result.as_explanation(getattr(criteria, "name", "profile"))
        return result

    def is_strict(self, criteria: InvestorCriteria, field_name: str) -> bool:
        strict = criteria.strict_fields or list(DEFAULT_STRICT_FIELDS)
        return field_name in strict

    def _fail_or_issue(
        self,
        field_name: str,
        criteria: InvestorCriteria,
        message: str,
        issues: list[str],
        failures: list[str],
        deductions: list[float],
    ) -> None:
        if self.is_strict(criteria, field_name):
            failures.append(message)
        else:
            issues.append(message)
            deductions.append(self.weights.get(field_name, 5))

    def _apply_exclusions(self, listing: Listing, criteria: InvestorCriteria, failures: list[str]) -> None:
        for rule in criteria.exclusion_rules or []:
            field_name = rule.get("field")
            operator = rule.get("operator", "eq")
            value = rule.get("value")
            reason = rule.get("reason") or f"Exclusion matched on {field_name}"
            actual = getattr(listing, field_name, None) if field_name else None
            if _rule_matches(actual, operator, value):
                failures.append(reason)

    def _compare_price(self, listing, criteria, reasons, issues, failures, deductions) -> None:
        price = listing.asking_price
        if criteria.min_price is not None:
            if price < criteria.min_price:
                self._fail_or_issue(
                    "min_price",
                    criteria,
                    f"Asking price {money_label(price)} below {money_label(criteria.min_price)} minimum",
                    issues,
                    failures,
                    deductions,
                )
            else:
                reasons.append(f"Asking price at or above {money_label(criteria.min_price)} minimum")
        ceiling = criteria.max_purchase_price or criteria.max_price
        field_name = "max_purchase_price" if criteria.max_purchase_price is not None else "max_price"
        if ceiling is not None:
            if price > ceiling:
                self._fail_or_issue(
                    field_name,
                    criteria,
                    f"Asking price {money_label(price)} exceeds {money_label(ceiling)} maximum",
                    issues,
                    failures,
                    deductions,
                )
            else:
                reasons.append(f"Asking price below {money_label(ceiling)} maximum")

    def _compare_geo(self, listing, criteria, reasons, issues, failures, deductions) -> None:
        zip_ok = True
        city_ok = True
        hood_ok = True
        if criteria.zip_codes:
            zip_ok = str(listing.zip_code) in {str(z) for z in criteria.zip_codes}
            if zip_ok:
                reasons.append(f"Target ZIP {listing.zip_code}")
        if criteria.cities:
            city_ok = _norm(listing.city) in {_norm(c) for c in criteria.cities}
            if city_ok:
                reasons.append(f"Target city {listing.city}")
        if criteria.neighborhoods:
            hood_ok = listing.neighborhood is not None and _norm(listing.neighborhood) in {
                _norm(n) for n in criteria.neighborhoods
            }
            if hood_ok:
                reasons.append(f"Target neighborhood {listing.neighborhood}")

        geo_filters = any([criteria.zip_codes, criteria.cities, criteria.neighborhoods])
        if not geo_filters:
            return
        any_match = (bool(criteria.zip_codes) and zip_ok) or (bool(criteria.cities) and city_ok) or (
            bool(criteria.neighborhoods) and hood_ok
        )
        if any_match:
            return
        if criteria.zip_codes and not zip_ok:
            self._fail_or_issue(
                "zip_codes",
                criteria,
                f"ZIP {listing.zip_code} is not in the target ZIP list",
                issues,
                failures,
                deductions,
            )
        elif criteria.cities and not city_ok:
            self._fail_or_issue(
                "cities",
                criteria,
                f"City {listing.city} is not in the target city list",
                issues,
                failures,
                deductions,
            )
        elif criteria.neighborhoods and not hood_ok:
            self._fail_or_issue(
                "neighborhoods",
                criteria,
                "Neighborhood is not in the preferred list",
                issues,
                failures,
                deductions,
            )

    def _compare_property_type(self, listing, criteria, reasons, issues, failures, deductions) -> None:
        if not criteria.property_types:
            return
        allowed = {_norm(item) for item in criteria.property_types}
        if _norm(listing.property_type) in allowed:
            reasons.append(f"Property type {listing.property_type} matches")
        else:
            self._fail_or_issue(
                "property_types",
                criteria,
                f"Property type {listing.property_type} is not in {sorted(allowed)}",
                issues,
                failures,
                deductions,
            )

    def _compare_beds_baths(self, listing, criteria, reasons, issues, failures, deductions) -> None:
        if criteria.min_bedrooms is not None:
            beds = listing.bedrooms if listing.bedrooms is not None else -1
            if beds >= criteria.min_bedrooms:
                reasons.append(f"{criteria.min_bedrooms} bedrooms required; listing has {listing.bedrooms}")
            else:
                self._fail_or_issue(
                    "min_bedrooms",
                    criteria,
                    f"{criteria.min_bedrooms} bedrooms required; listing has {listing.bedrooms}",
                    issues,
                    failures,
                    deductions,
                )
        if criteria.min_bathrooms is not None:
            baths = float(listing.bathrooms) if listing.bathrooms is not None else -1
            if baths >= float(criteria.min_bathrooms):
                reasons.append(f"{criteria.min_bathrooms} bathrooms required; listing has {listing.bathrooms}")
            else:
                self._fail_or_issue(
                    "min_bathrooms",
                    criteria,
                    f"{criteria.min_bathrooms} bathrooms required; listing has {listing.bathrooms}",
                    issues,
                    failures,
                    deductions,
                )

    def _compare_size(self, listing, criteria, reasons, issues, failures, deductions) -> None:
        if criteria.min_sqft is not None:
            if listing.sqft is not None and listing.sqft >= criteria.min_sqft:
                reasons.append(f"Living area {listing.sqft:,} sq ft meets {criteria.min_sqft:,} minimum")
            else:
                self._fail_or_issue(
                    "min_sqft",
                    criteria,
                    f"Living area {listing.sqft} is below {criteria.min_sqft} sq ft minimum",
                    issues,
                    failures,
                    deductions,
                )
        if criteria.max_sqft is not None and listing.sqft is not None and listing.sqft > criteria.max_sqft:
            self._fail_or_issue(
                "max_sqft",
                criteria,
                f"Living area {listing.sqft} exceeds {criteria.max_sqft} sq ft maximum",
                issues,
                failures,
                deductions,
            )
        if criteria.min_lot_sqft is not None:
            if listing.lot_sqft is not None and listing.lot_sqft >= criteria.min_lot_sqft:
                reasons.append("Lot size meets minimum")
            else:
                self._fail_or_issue(
                    "min_lot_sqft",
                    criteria,
                    "Lot size below minimum",
                    issues,
                    failures,
                    deductions,
                )

    def _compare_year(self, listing, criteria, reasons, issues, failures, deductions) -> None:
        if criteria.year_built_min is not None:
            if listing.year_built is not None and listing.year_built >= criteria.year_built_min:
                reasons.append(f"Year built {listing.year_built} meets {criteria.year_built_min}+ preference")
            else:
                self._fail_or_issue(
                    "year_built_min",
                    criteria,
                    f"Property built in {listing.year_built}; investor preference is {criteria.year_built_min}+",
                    issues,
                    failures,
                    deductions,
                )
        if criteria.year_built_max is not None and listing.year_built and listing.year_built > criteria.year_built_max:
            self._fail_or_issue(
                "year_built_max",
                criteria,
                f"Property built in {listing.year_built}; investor maximum is {criteria.year_built_max}",
                issues,
                failures,
                deductions,
            )

    def _compare_hoa(self, listing, criteria, reasons, issues, failures, deductions) -> None:
        if criteria.hoa_required is False and listing.hoa_monthly and listing.hoa_monthly > 0:
            self._fail_or_issue(
                "hoa_required",
                criteria,
                "HOA present; investor does not want HOA",
                issues,
                failures,
                deductions,
            )
        elif criteria.hoa_required is False:
            reasons.append("No HOA restriction conflict")
        if criteria.max_hoa is not None:
            hoa = listing.hoa_monthly or Decimal("0")
            if hoa <= criteria.max_hoa:
                reasons.append(f"HOA {money_label(hoa)} within {money_label(criteria.max_hoa)} cap")
            else:
                self._fail_or_issue(
                    "max_hoa",
                    criteria,
                    f"HOA {money_label(hoa)} exceeds {money_label(criteria.max_hoa)}",
                    issues,
                    failures,
                    deductions,
                )

    def _compare_dom_and_reductions(self, listing, criteria, reasons, issues, failures, deductions) -> None:
        if criteria.max_dom is not None:
            if listing.days_on_market is not None and listing.days_on_market <= criteria.max_dom:
                reasons.append(f"Days on market {listing.days_on_market} within {criteria.max_dom}")
            else:
                self._fail_or_issue(
                    "max_dom",
                    criteria,
                    f"Days on market {listing.days_on_market} exceeds {criteria.max_dom}",
                    issues,
                    failures,
                    deductions,
                )
        if criteria.require_price_reduction:
            reduced = listing.previous_price is not None and listing.asking_price < listing.previous_price
            if reduced:
                reasons.append("Price reduction present")
            else:
                self._fail_or_issue(
                    "price_reduction",
                    criteria,
                    "No price reduction on this listing",
                    issues,
                    failures,
                    deductions,
                )

    def _compare_financials(self, listing, criteria, reasons, issues, failures, deductions) -> None:
        if criteria.min_estimated_rent is not None:
            if listing.estimated_rent is not None and listing.estimated_rent >= criteria.min_estimated_rent:
                reasons.append("Estimated rent exceeds minimum")
            else:
                self._fail_or_issue(
                    "min_estimated_rent",
                    criteria,
                    "Estimated rent below minimum or unavailable",
                    issues,
                    failures,
                    deductions,
                )
        if criteria.min_cap_rate is not None:
            if listing.cap_rate is not None and listing.cap_rate >= criteria.min_cap_rate:
                reasons.append("Cap rate meets minimum")
            else:
                self._fail_or_issue(
                    "min_cap_rate",
                    criteria,
                    "Cap rate below minimum or unavailable",
                    issues,
                    failures,
                    deductions,
                )
        if criteria.max_grm is not None:
            if listing.grm is not None and listing.grm <= criteria.max_grm:
                reasons.append("GRM within maximum")
            else:
                self._fail_or_issue(
                    "max_grm",
                    criteria,
                    "GRM above maximum or unavailable",
                    issues,
                    failures,
                    deductions,
                )
        if criteria.max_repair_estimate is not None and listing.repair_estimate is not None:
            if listing.repair_estimate <= criteria.max_repair_estimate:
                reasons.append("Repair estimate within tolerance")
            else:
                self._fail_or_issue(
                    "max_repair_estimate",
                    criteria,
                    "Repair estimate exceeds tolerance",
                    issues,
                    failures,
                    deductions,
                )
        if criteria.occupancy_statuses:
            allowed = {_norm(item) for item in criteria.occupancy_statuses}
            if listing.occupancy_status and _norm(listing.occupancy_status) in allowed:
                reasons.append(f"Occupancy {listing.occupancy_status} accepted")
            else:
                self._fail_or_issue(
                    "occupancy_status",
                    criteria,
                    "Occupancy status is not preferred",
                    issues,
                    failures,
                    deductions,
                )

    def _compare_flags(self, listing, criteria, reasons, issues, deductions) -> None:
        dummy_failures: list[str] = []
        if criteria.seller_financing_preferred and not listing.seller_financing:
            self._fail_or_issue(
                "seller_financing",
                criteria,
                "Seller financing not offered",
                issues,
                dummy_failures,
                deductions,
            )
        elif listing.seller_financing:
            reasons.append("Seller financing available")
        if criteria.foreclosure_preferred and not listing.foreclosure:
            self._fail_or_issue(
                "foreclosure",
                criteria,
                "Not a foreclosure",
                issues,
                dummy_failures,
                deductions,
            )
        if criteria.short_sale_preferred and not listing.short_sale:
            self._fail_or_issue(
                "short_sale",
                criteria,
                "Not a short sale",
                issues,
                dummy_failures,
                deductions,
            )
        if criteria.assumable_loan_preferred and not listing.assumable_loan:
            self._fail_or_issue(
                "assumable_loan",
                criteria,
                "Loan is not assumable",
                issues,
                dummy_failures,
                deductions,
            )


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _rule_matches(actual: Any, operator: str, expected: Any) -> bool:
    if actual is None:
        return False
    if operator == "eq":
        return _norm(actual) == _norm(expected)
    if operator == "neq":
        return _norm(actual) != _norm(expected)
    if operator == "in":
        return _norm(actual) in {_norm(item) for item in expected}
    if operator == "not_in":
        return _norm(actual) not in {_norm(item) for item in expected}
    try:
        left = Decimal(str(actual))
        right = Decimal(str(expected))
    except Exception:
        return False
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    return False
