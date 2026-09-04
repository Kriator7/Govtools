"""Telegram copy and commands for PirateEye public home hunt."""

from __future__ import annotations

from app.models.seller_lead import SellerLead
from app.utilities.money import money_label

HELP_TEXT = (
    "PirateEye investor hunt (@PirateEye_bot)\n"
    "\n"
    "MLS is not a live feed yet (MLS_PROVIDER=mock). We will not scrape Matrix.\n"
    "Hunt public sources instead:\n"
    "/hunt — obituaries, FSBO, HUD/REO, probate notices\n"
    "/obits — Clark County obituaries (estate-watch, review only)\n"
    "/fsbo — Las Vegas for-sale-by-owner (Craigslist RSS)\n"
    "/hud — HUD / government-owned home mentions\n"
    "/leads — stored leads\n"
    "/mls — MLS status\n"
    "\n"
    "Obituaries are review-only. Do not auto-contact family. "
    "Open the notice, then search the public Clark County Assessor. "
    "HUD inventory: hudhomestore.gov (Nevada map). Bids need a HUD NAID broker. "
    "Investor SMS still needs your APPROVE."
)

START_TEXT = (
    "Linked as PirateEye operator.\n"
    "Listing alerts and open-lead hunt land here.\n"
    "MLS is still mock — use /hunt for public obituaries, FSBO, HUD, and probate notices.\n"
    "Approve / Reject / Snooze on investor-match cards.\n"
    "Send /help for commands."
)

MLS_STATUS_TEXT = (
    "MLS status: mock. No authorized Trestle/IDX feed is connected.\n"
    "Do not scrape Las Vegas REALTORS Matrix.\n"
    "Use /hunt for public sources until Damian or the broker enables option 3 only."
)

SOURCE_LABELS = {
    "obituary": "Obituary / estate-watch",
    "fsbo": "FSBO (Craigslist)",
    "hud": "HUD / REO mention",
    "probate": "Probate / trustee / foreclosure notice",
}

COMMAND_SOURCES = {
    "/hunt": None,
    "/obits": "obituary",
    "/obituary": "obituary",
    "/obituaries": "obituary",
    "/fsbo": "fsbo",
    "/hud": "hud",
    "/probate": "probate",
}

HUNT_PHRASES = frozenset(
    {
        "hunt",
        "find houses",
        "find homes",
        "find listings",
        "look for houses",
        "look for homes",
        "search houses",
        "search homes",
    }
)
OBIT_PHRASES = frozenset({"obits", "obituary", "obituaries", "estate watch", "who died"})


def command_name(text: str) -> str:
    token = (text or "").strip().split()[0] if text else ""
    token = token.split("@", 1)[0].lower()
    return token


def hunt_source_for_text(text: str) -> str | None | str:
    """Return source name, None for all sources, or 'help'/'mls'/'leads'."""
    command = command_name(text)
    if command in {"/help", "help"}:
        return "help"
    if command in {"/mls", "/idx"}:
        return "mls"
    if command in {"/leads", "/lead"}:
        return "leads"
    if command in COMMAND_SOURCES:
        return COMMAND_SOURCES[command]
    lowered = " ".join((text or "").strip().lower().split())
    if lowered in OBIT_PHRASES or lowered.startswith("obituar"):
        return "obituary"
    if lowered in HUNT_PHRASES:
        return None
    if lowered in {"fsbo", "for sale by owner"}:
        return "fsbo"
    return "unknown"


def summary_text(result: dict, *, source: str | None) -> str:
    label = SOURCE_LABELS.get(source or "", "public sources")
    if source is None:
        label = "obituaries, FSBO, HUD/REO, probate notices"
    lines = [
        f"PirateEye hunt — {label}",
        f"Scanned {result.get('scanned', 0)} · new {result.get('created', 0)} · "
        f"listed {result.get('converted', 0)}",
    ]
    by_source = result.get("by_source") or {}
    if by_source:
        parts = [f"{name} {count}" for name, count in sorted(by_source.items())]
        lines.append("Sources: " + ", ".join(parts))
    errors = result.get("errors") or []
    if errors:
        lines.append("Fetch notes: " + "; ".join(errors[:3]))
    if not result.get("scanned"):
        lines.append("No public items this pass. Check OPEN_LEADS_MODE or try /leads.")
    lines.append("Obituary/probate cards are review-only. No family is contacted.")
    return "\n".join(lines)


def lead_card(lead: SellerLead) -> tuple[str, list[list[dict[str, str]]]]:
    kind = SOURCE_LABELS.get(lead.source, lead.source)
    price = money_label(lead.asking_price) if lead.asking_price is not None else "price n/a"
    place = ", ".join(part for part in [lead.street_address, lead.city, lead.state] if part) or lead.city or "Clark County, NV"
    lines = [
        f"{kind} · {lead.public_id}",
        lead.title,
        place,
        price,
    ]
    if lead.person_name:
        lines.append(f"Name on notice: {lead.person_name}")
    if lead.review_only:
        lines.append("Review only. Do not auto-contact next of kin.")
        lines.append("Next: open the notice, then search Clark County Assessor.")
    elif lead.listing_id is not None:
        lines.append("Address+price parsed — stored as an open listing for investor match.")
    if lead.summary and lead.summary != lead.title:
        lines.append(lead.summary[:280])
    buttons: list[list[dict[str, str]]] = []
    if lead.url:
        buttons.append([{"text": "OPEN SOURCE", "url": lead.url}])
    if lead.assessor_url:
        buttons.append([{"text": "ASSESSOR SEARCH", "url": lead.assessor_url}])
    buttons.append(
        [
            {"text": "KEEP", "callback_data": f"lead:keep:{lead.public_id}"},
            {"text": "DISMISS", "callback_data": f"lead:dismiss:{lead.public_id}"},
        ]
    )
    return "\n".join(lines), buttons


def empty_leads_text(source: str | None) -> str:
    if source:
        return f"No stored {source} leads yet. Send /hunt or /{source if source != 'obituary' else 'obits'}."
    return "No stored public leads yet. Send /hunt."
