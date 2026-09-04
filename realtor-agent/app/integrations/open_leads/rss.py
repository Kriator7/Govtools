"""Fetch and parse public RSS/Atom feeds.

Google News RSS: https://news.google.com/rss
Craigslist search RSS: https://www.craigslist.org/about/rss
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

import httpx

USER_AGENT = (
    "PirateEye/0.1 (realtor-agent open-lead hunt; public RSS only; "
    "+https://t.me/PirateEye_bot)"
)

_DC = "{http://purl.org/dc/elements/1.1/}"


def fingerprint_for(*parts: str) -> str:
    blob = "|".join(part.strip().lower() for part in parts if part)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def fetch_text(url: str, *, timeout: float = 20.0, client: httpx.Client | None = None) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"}
    if client is not None:
        response = client.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as owned:
        response = owned.get(url)
        response.raise_for_status()
        return response.text


def parse_feed_items(xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    items: list[dict[str, Any]] = []
    for node in list(root.iter()):
        tag = _local(node.tag)
        if tag == "item":
            items.append(_rss_item(node))
        elif tag == "entry":
            items.append(_atom_entry(node))
    return [item for item in items if item.get("title") or item.get("link")]


def parse_datetime(value: str | None) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        iso = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if iso.tzinfo is None:
            return iso.replace(tzinfo=timezone.utc)
        return iso.astimezone(timezone.utc)
    except ValueError:
        return None


def strip_html(blob: str) -> str:
    text = re.sub(r"<[^>]+>", " ", blob or "")
    return re.sub(r"\s+", " ", text).strip()


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _child_text(node: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in list(node):
        if _local(child.tag).lower() in wanted:
            href = child.attrib.get("href")
            if href and not (child.text or "").strip():
                return href
            return "".join(child.itertext()).strip()
    return ""


def _rss_item(node: ET.Element) -> dict[str, Any]:
    link = _child_text(node, "link", "guid")
    return {
        "title": _child_text(node, "title"),
        "link": link,
        "description": strip_html(_child_text(node, "description", "summary")),
        "published": _child_text(node, "pubDate", "date", "dc:date")
        or _namespaced_text(node, _DC, "date"),
        "source": _child_text(node, "source"),
    }


def _atom_entry(node: ET.Element) -> dict[str, Any]:
    link = _child_text(node, "link")
    if not link:
        for child in list(node):
            if _local(child.tag) == "link" and child.attrib.get("href"):
                link = child.attrib["href"]
                break
    return {
        "title": _child_text(node, "title"),
        "link": link,
        "description": strip_html(_child_text(node, "summary", "content")),
        "published": _child_text(node, "updated", "published"),
        "source": "",
    }


def _namespaced_text(node: ET.Element, ns: str, local: str) -> str:
    child = node.find(f"{ns}{local}")
    if child is None:
        return ""
    return "".join(child.itertext()).strip()
