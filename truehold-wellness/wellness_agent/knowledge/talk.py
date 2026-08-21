"""Floor-team customer talk: approved retrieval, optional small LLM, never dosing.

LLM is opt-in via WELLNESS_LLM_API_KEY (OpenAI-compatible, default xAI).
If the key is missing, the host uses approved seed lines only.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

from wellness_agent.greetings import (
    fasting_answer,
    is_bio_request,
    is_creed_request,
    is_fasting_request,
    is_herb_request,
)
from wellness_agent.discounts import COLLEGE_POLICY, extract_code
from wellness_agent.knowledge import active_promo, pick_snippet, retrieve, seed_approved_knowledge
from wellness_agent.knowledge.house import (
    FASTING_OPENER,
    format_fasting_followup,
    format_host_bio,
    peptide_record,
)
from wellness_agent.session_store import focus_sku
from wellness_agent.team import current_host, flavor_caption

# Block chat-side protocol talk. Vial sizes like "20 mg" in catalog lines are allowed in retrieval,
# but generated replies may not walk someone through mix math.
_BLOCK = re.compile(
    r"\b(reconstitut|bacteriostatic|bac water|inject|syringe|units?\s*=|mcg/|iu\b|dose of|take \d)\b",
    re.I,
)


@dataclass
class TalkReply:
    text: str
    pose: str
    source: str


def llm_configured() -> bool:
    return bool(os.environ.get("WELLNESS_LLM_API_KEY") or os.environ.get("XAI_API_KEY"))


def reply(
    message: str,
    *,
    chat_id: str = "",
    greet: bool = False,
    host: dict[str, Any] | None = None,
) -> TalkReply:
    seed_approved_knowledge()
    host = host or current_host(chat_id)
    text = (message or "").strip()
    lowered = text.lower()
    if greet:
        joke = abs(hash(f"{chat_id}:joke:{host['id']}")) % 4 == 0
        body = flavor_caption(host, "wave", joke=joke)
        promo = _promo_line(chat_id, sprinkle=True)
        if promo:
            body = f"{body}\n\n{promo}"
        return TalkReply(text=body, pose="wave", source="seed-hello")
    if is_creed_request(text):
        return _creed_reply(host, text)
    if extract_code(text) or _is_discount_question(lowered):
        body = COLLEGE_POLICY
        extra = _promo_line(chat_id, sprinkle=False)
        if extra:
            body = f"{body}\n\n{extra}"
        return TalkReply(text=_signed(host, body), pose="present", source="seed-discount")
    focused = peptide_record(focus_sku(chat_id) or "") if chat_id else peptide_record("")
    if focused.get("weight_loss"):
        answer = fasting_answer(text)
        if answer is not None:
            return TalkReply(
                text=_signed(host, format_fasting_followup(experienced=answer)),
                pose="think",
                source="seed-fasting",
            )
    if is_bio_request(text):
        return TalkReply(text=format_host_bio(host), pose="present", source="seed-bio")
    if is_fasting_request(text):
        hits = retrieve(text) or retrieve("intermittent fasting eating window")
        top = next((row for row in hits if row.get("kind") == "fasting"), hits[0] if hits else None)
        body = format_fasting_followup(experienced=True)
        if top:
            body = f"<b>{top['title']}</b>\n{top['text']}\n\n<b>{FASTING_OPENER}</b>"
        return TalkReply(text=_signed(host, body), pose="think", source="seed-fasting")
    if is_herb_request(text):
        hits = retrieve(text)
        herb_hits = [row for row in hits if row.get("kind") == "herb"]
        if herb_hits:
            lines = [f"<b>{row['title']}</b>\n{row['text']}" for row in herb_hits[:3]]
            lines.append("Kitchen/educational only. Not a prescription. Mix math stays on Sheet.")
            return TalkReply(text=_signed(host, "\n\n".join(lines)), pose="think", source="seed-herb")
    if re.search(r"\b(thanks|thank you|thx|appreciate)\b", lowered):
        return TalkReply(
            text=_signed(host, pick_snippet("thanks", salt=chat_id)),
            pose="soon",
            source="seed-thanks",
        )
    hits = retrieve(text)
    if llm_configured():
        generated = _llm_reply(text, hits, host)
        if generated:
            return generated
    if hits and hits[0]["kind"] == "product":
        product = hits[0]
        source = str(product.get("source") or "")
        sku = source.split(":", 1)[1] if source.startswith("catalog:") else ""
        rec = peptide_record(sku)
        opener = rec["opener"] if sku else "Tap the name on the menu, or Sheet for the locked file."
        return TalkReply(
            text=_signed(
                host,
                f"<b>{product['title']}</b>\n"
                f"{product['text']}\n\n"
                f"<b>{opener}</b>\n"
                "Tap the name on the menu, or Sheet for the locked file.",
            ),
            pose="present",
            source="seed-product",
        )
    if hits:
        top = hits[0]
        return TalkReply(
            text=_signed(host, f"<b>{top['title']}</b>\n{top['text']}"),
            pose="think",
            source=f"seed-{top['kind']}",
        )
    small = pick_snippet("smalltalk", salt=text)
    promo = _promo_line(chat_id, sprinkle=True)
    body = small or "<b>I am here.</b>\nTap a colorful button — that is the easy path."
    if promo:
        body = f"{body}\n\n{promo}"
    return TalkReply(text=_signed(host, body), pose="present", source="seed-smalltalk")


def _creed_reply(host: dict[str, Any], message: str) -> TalkReply:
    hits = retrieve(message)
    house = next((row for row in hits if row.get("kind") == "creed"), None)
    if house is None:
        fallback = retrieve("nature peptides truth empowerment vitamin")
        house = next((row for row in fallback if row.get("kind") == "creed"), None)
        if house is None and fallback:
            house = fallback[0]
    body = f"<i>{host.get('creed') or ''}</i>".strip()
    if house:
        body = f"{body}\n\n<b>{house['title']}</b>\n{house['text']}" if body else f"<b>{house['title']}</b>\n{house['text']}"
    if not body:
        body = "We care that you get healthy. Tap Sheet for the locked file, Team for a person."
    return TalkReply(text=_signed(host, body), pose="think", source="seed-creed")


def _signed(host: dict[str, Any], text: str) -> str:
    return f"<b>{host['icon']} {host['name']}</b>\n{text}"


def _is_discount_question(lowered: str) -> bool:
    return bool(
        re.search(
            r"\b(discount|promo code|coupon|college student|student discount|"
            r"10%\s*off|percent off|sale|sales)\b",
            lowered,
        )
    )


def _promo_line(chat_id: str, *, sprinkle: bool) -> str:
    promo = active_promo()
    if not promo:
        return ""
    if sprinkle and abs(hash(f"promo:{chat_id}")) % 5:
        return ""
    return f"<b>Staff-approved note</b>\n{promo['headline']}\n{promo['body']}"


def _llm_reply(message: str, hits: list[dict[str, Any]], host: dict[str, Any]) -> TalkReply | None:
    context = "\n\n".join(f"[{row['kind']}] {row['title']}: {row['text']}" for row in hits) or "No extra snippets."
    promo = active_promo()
    standing = f"Approved standing discount: {COLLEGE_POLICY}"
    extra = (
        f"Approved promotion: {promo['headline']} — {promo['body']}"
        if promo
        else "No extra promotion beyond the college code."
    )
    promo_block = f"{standing}\n{extra}"
    name = str(host.get("name") or "Theo")
    role = str(host.get("role") or "floor host")
    creed = str(host.get("creed") or "")
    system = (
        f"You are {name}, {role} at TrueHold Wellness on Telegram. "
        "Warm, brief, playful, never sad or dry. One short HTML <b> heading plus a few lines. "
        f"House voice: {creed} "
        "We care that people get healthy, and we walk with them. "
        "Nature and God gave the tools. Science recovered what broths, herbs, and fermentation once knew. "
        "Most peptides already exist in the body. Too much of anything, even oxygen, can harm you. "
        "If you use a quotation, copy it exactly from approved context and keep the author and work credit. "
        "Never invent a quote. Never post a quote without naming who said it. "
        "Empowerment, ownership, high-quality food and rest. "
        "If they support this house, invite them to tell others — gently. "
        "Every host pulls fasting, herb, and peptide-prep notes from the same approved house database. "
        "Weight-loss vials (tirzepatide, retatrutide) must include a kind question: Have you ever tried fasting, even a little? We're here either way. "
        "Kitchen herbs are educational food talk, never a dose. "
        "The floor team is backed by over 50 years of combined clinical, medical, and surgical experience. "
        "Use ONLY the approved context. If it is not there, say you will fetch a person via Team "
        "and offer the tap-menu. Never give dosing, reconstitution, injection, or medical advice. "
        "Never invent products, prices, or sales other than the approved college code ADPILV2026 (10% off). "
        "Never include http links. "
        "Las Vegas residents, dry vials only, educational only. Under 500 characters."
    )
    user = f"Approved context:\n{context}\n\n{promo_block}\n\nCustomer: {message}"
    try:
        content = _chat(system, user)
    except Exception:
        return None
    if not content or _BLOCK.search(content) or "http" in content.lower():
        return None
    if hits and hits[0]["kind"] == "product":
        pose = "work"
    elif hits and hits[0]["kind"] == "policy":
        pose = "think"
    else:
        pose = "present"
    return TalkReply(text=_signed(host, content.strip()), pose=pose, source="llm")


def _chat(system: str, user: str) -> str:
    """OpenAI-compatible chat. Default host is xAI.

    https://docs.x.ai/docs/api-reference
    """
    key = os.environ.get("WELLNESS_LLM_API_KEY") or os.environ.get("XAI_API_KEY") or ""
    base = os.environ.get("WELLNESS_LLM_BASE_URL") or "https://api.x.ai/v1"
    model = os.environ.get("WELLNESS_LLM_MODEL") or "grok-4-1-fast"
    with httpx.Client(timeout=20) as client:
        response = client.post(
            f"{base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0.6,
                "max_tokens": 220,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
    return str((((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or "")
