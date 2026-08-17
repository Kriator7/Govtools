#!/usr/bin/env python3
"""Authenticate and fetch from the configured MLS provider (mock by default)."""

from app.services.providers import get_mls_provider


def main() -> int:
    provider = get_mls_provider()
    print({"provider": provider.name, "authenticated": provider.authenticate()})
    listings = provider.fetch_new_listings()
    print({"count": len(listings)})
    if listings:
        normalized = provider.normalize_listing(listings[0])
        print({"sample_mls_id": normalized.mls_listing_id, "city": normalized.city})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
