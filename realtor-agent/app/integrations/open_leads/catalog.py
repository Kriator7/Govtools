"""Catalog of PirateEye public-lead providers."""

from __future__ import annotations

from collections.abc import Iterable

from app.config import get_settings
from app.integrations.open_leads.base import OpenLeadProvider
from app.integrations.open_leads.fixture import FixtureOpenLeadProvider
from app.integrations.open_leads.rss_providers import (
    fsbo_provider,
    hud_provider,
    obituary_provider,
    probate_provider,
)

SOURCE_NAMES = ("obituary", "fsbo", "hud", "probate")


def providers_for(source: str | None = None, *, mode: str | None = None) -> list[OpenLeadProvider]:
    settings = get_settings()
    mode = (mode or settings.open_leads_mode or "live").strip().lower()
    wanted = {source} if source else set(SOURCE_NAMES)
    if mode == "fixture":
        rows: list[OpenLeadProvider] = []
        for name in SOURCE_NAMES:
            if name in wanted:
                rows.append(FixtureOpenLeadProvider(source=name))
        return rows
    live: dict[str, OpenLeadProvider] = {
        "obituary": obituary_provider(),
        "fsbo": fsbo_provider(),
        "hud": hud_provider(),
        "probate": probate_provider(),
    }
    return [live[name] for name in SOURCE_NAMES if name in wanted]


def iter_named(source: str | None = None, *, mode: str | None = None) -> Iterable[tuple[str, OpenLeadProvider]]:
    for provider in providers_for(source, mode=mode):
        yield provider.name if provider.name != "fixture" else source or provider.name, provider
