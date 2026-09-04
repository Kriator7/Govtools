"""Clark County / Las Vegas market for PirateEye open-lead hunt."""

from __future__ import annotations

from urllib.parse import quote_plus, urlencode

# Clark County Assessor (public portal — do not scrape):
# https://www.clarkcountynv.gov/government/departments/assessor/
CLARK_ASSESSOR_PORTAL = "https://www.clarkcountynv.gov/government/departments/assessor/"

# Google News RSS: https://news.google.com/rss
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"

LAS_VEGAS_CITIES = (
    "Las Vegas",
    "Henderson",
    "North Las Vegas",
    "Boulder City",
    "Summerlin",
    "Paradise",
    "Spring Valley",
    "Enterprise",
)


def google_news_rss(query: str) -> str:
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    return f"{GOOGLE_NEWS_RSS}?{urlencode(params)}"


def obituary_rss_url() -> str:
    return google_news_rss(
        'obituary (Las Vegas OR Henderson OR "North Las Vegas" OR "Clark County" OR "Boulder City")'
    )


def hud_rss_url() -> str:
    return google_news_rss(
        '("HUD home" OR "HUD homes" OR "government owned" OR REO) (Las Vegas OR Henderson OR "Clark County") (sale OR sold OR listing)'
    )


def probate_rss_url() -> str:
    return google_news_rss(
        '(probate OR "estate sale" OR "trustee sale" OR foreclosure OR "notice of default") (Las Vegas OR Henderson OR "Clark County")'
    )


def craigslist_fsbo_rss_url() -> str:
    # Craigslist RSS is a public search export. reo = real estate by owner.
    return "https://lasvegas.craigslist.org/search/reo?format=rss"


def assessor_search_url(person_or_address: str) -> str:
    """Public web search pointed at Clark County assessor records. Do not scrape."""
    needle = (person_or_address or "").strip()
    if not needle:
        return CLARK_ASSESSOR_PORTAL
    q = quote_plus(f'site:clarkcountynv.gov assessor "{needle}"')
    return f"https://www.google.com/search?q={q}"


def city_from_text(text: str) -> str | None:
    blob = text or ""
    for city in LAS_VEGAS_CITIES:
        if city.lower() in blob.lower():
            return city
    if "clark county" in blob.lower():
        return "Las Vegas"
    return None
