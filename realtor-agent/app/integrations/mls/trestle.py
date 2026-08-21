"""Authorized Trestle RESO WebAPI adapter (Cotality).

Token: POST https://api.cotality.com/trestle/oidc/connect/token
OData: https://api.cotality.com/trestle/odata/
Do not scrape Matrix. Never invent ARV.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.integrations.mls.base import MLSProvider, NormalizedListingDraft
from app.services.inbox.mls_access import DEFAULT_ODATA_URL, DEFAULT_TOKEN_URL
from app.services.matching.screening import normalize_property_type

ACTIVE_CITIES_FILTER = (
    "StandardStatus eq 'Active' and ("
    "City eq 'Las Vegas' or City eq 'North Las Vegas' or City eq 'Henderson')"
)
PROPERTY_SELECT = (
    "ListingId,ListingKey,UnparsedAddress,StreetNumber,StreetName,StreetSuffix,"
    "City,StateOrProvince,PostalCode,ListPrice,PropertyType,PropertySubType,"
    "BedroomsTotal,BathroomsTotalInteger,LivingArea,LotSizeSquareFeet,YearBuilt,"
    "StandardStatus,OnMarketDate,DaysOnMarket,AssociationFee,Latitude,Longitude,"
    "PublicRemarks,PrivateRemarks,ListingURL"
)


class TrestleMLSProvider(MLSProvider):
    name = "trestle"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or httpx.Client(timeout=30.0)
        self._token: str | None = None

    def authenticate(self) -> bool:
        return bool(self._access_token())

    def fetch_new_listings(self, since: datetime | None = None) -> list[dict[str, Any]]:
        token = self._access_token()
        if not token:
            return []
        params = {
            "$filter": ACTIVE_CITIES_FILTER,
            "$top": "25",
            "$select": PROPERTY_SELECT,
        }
        if since is not None:
            stamp = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            params["$filter"] = f"{ACTIVE_CITIES_FILTER} and ModificationTimestamp gt {stamp}"
        response = self.client.get(
            self._odata_url().rstrip("/") + "/Property",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params=params,
        )
        if response.status_code >= 400:
            return []
        payload = response.json()
        rows = payload.get("value") if isinstance(payload, dict) else payload
        return [item for item in (rows or []) if isinstance(item, dict)]

    def fetch_updated_listings(self, since: datetime | None = None) -> list[dict[str, Any]]:
        return self.fetch_new_listings(since=since)

    def get_listing(self, mls_listing_id: str) -> dict[str, Any] | None:
        token = self._access_token()
        if not token:
            return None
        listing_id = str(mls_listing_id).replace("'", "''")
        response = self.client.get(
            self._odata_url().rstrip("/") + "/Property",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params={"$filter": f"ListingId eq '{listing_id}'", "$top": "1", "$select": PROPERTY_SELECT},
        )
        if response.status_code >= 400:
            return None
        rows = (response.json() or {}).get("value") or []
        return rows[0] if rows else None

    def normalize_listing(self, raw: dict[str, Any]) -> NormalizedListingDraft:
        street = str(raw.get("UnparsedAddress") or "").strip()
        if not street:
            street = " ".join(
                str(part).strip()
                for part in (raw.get("StreetNumber"), raw.get("StreetName"), raw.get("StreetSuffix"))
                if part
            ).strip()
        subtype = raw.get("PropertySubType") or raw.get("PropertyType") or "single_family"
        listing_date = _parse_dt(raw.get("OnMarketDate"))
        return NormalizedListingDraft(
            mls_listing_id=str(raw.get("ListingId") or raw.get("ListingKey") or ""),
            street_address=street or "Unknown",
            city=str(raw.get("City") or ""),
            state=str(raw.get("StateOrProvince") or "NV"),
            zip_code=str(raw.get("PostalCode") or ""),
            asking_price=_decimal(raw.get("ListPrice")) or Decimal("0"),
            property_type=normalize_property_type(subtype) or "single_family",
            bedrooms=_int(raw.get("BedroomsTotal")),
            bathrooms=_float(raw.get("BathroomsTotalInteger")),
            sqft=_int(raw.get("LivingArea")),
            lot_sqft=_int(raw.get("LotSizeSquareFeet")),
            year_built=_int(raw.get("YearBuilt")),
            days_on_market=_int(raw.get("DaysOnMarket")),
            listing_status=str(raw.get("StandardStatus") or "active").lower(),
            listing_date=listing_date,
            hoa_monthly=_decimal(raw.get("AssociationFee")),
            latitude=_float(raw.get("Latitude")),
            longitude=_float(raw.get("Longitude")),
            remarks=raw.get("PublicRemarks"),
            agent_remarks=raw.get("PrivateRemarks"),
            listing_url=raw.get("ListingURL"),
            raw_payload=raw,
            provider=self.name,
        )

    def health(self) -> tuple[str, str]:
        try:
            ok = self.authenticate()
            return ("ok", "authenticated") if ok else ("error", "authentication failed")
        except Exception:  # noqa: BLE001
            return ("error", "authentication failed")

    def _access_token(self) -> str | None:
        if self._token:
            return self._token
        api_key = (self.settings.mls_api_key or "").strip()
        client_id = (self.settings.mls_client_id or "").strip()
        client_secret = (self.settings.mls_client_secret or "").strip()
        if client_id and client_secret:
            response = self.client.post(
                self._token_url(),
                data={
                    "grant_type": "client_credentials",
                    "scope": self.settings.mls_oauth_scope or "api",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code >= 400:
                return None
            token = (response.json() or {}).get("access_token")
            if token:
                self._token = str(token)
                return self._token
        if api_key:
            probe = self.client.get(
                self._odata_url().rstrip("/") + "/",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            )
            if probe.status_code < 400:
                self._token = api_key
                return self._token
        return None

    def _odata_url(self) -> str:
        return (self.settings.mls_api_base_url or DEFAULT_ODATA_URL).rstrip("/") + "/"

    def _token_url(self) -> str:
        return self.settings.mls_token_url or DEFAULT_TOKEN_URL


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
