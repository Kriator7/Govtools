"""Theo's customer talk: approved retrieval, optional small LLM, never dosing.

LLM is opt-in via WELLNESS_LLM_API_KEY (OpenAI-compatible, default xAI).
If the key is missing, Theo uses approved seed lines only.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

from wellness_agent.knowledge import active_promo, pick_snippet, retrieve, seed_approved_knowledge

AGENT_NAME = "Theo"
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


def reply(message: str, *, chat_id: str = "", greet: bool = False) -> TalkReply:
    seed_approved_knowledge()
    text = (message or "").strip()
    lowered = text.lower()
    if greet:
        hello = pick_snippet("hello", salt=f"{chat_id}:{text}")
        joke = pick_snippet("joke", salt=f"{chat_id}:joke") if abs(hash(chat_id)) % 4 == 0 else ""
        promo = _promo_line(chat_id, sprinkle=True)
        body = hello
        if joke:
            body = f"{hello}\n\n<i>{joke}</i>"
        if promo:
            body = f"{body}\n\n{promo}"
        return TalkReply(text=body, pose="wave", source="seed-hello")
    if re.search(r"\b(thanks|thank you|thx|appreciate)\b", lowered):
        return TalkReply(text=pick_snippet("thanks", salt=chat_id), pose="wave", source="seed-thanks")
    hits = retrieve(text)
    if llm_configured():
        generated = _llm_reply(text, hits)
        if generated:
            return generated
    if hits and hits[0]["kind"] == "product":
        product = hits[0]
        return TalkReply(
            text=(
                f"<b>{product['title']}</b>\n"
                f"{product['text']}\n"
                "Tap the name on the menu, or Sheet for the locked file."
            ),
            pose="present",
            source="seed-product",
        )
    if hits:
        top = hits[0]
        return TalkReply(
            text=f"<b>{top['title']}</b>\n{top['text']}",
            pose="think",
            source=f"seed-{top['kind']}",
        )
    small = pick_snippet("smalltalk", salt=text)
    promo = _promo_line(chat_id, sprinkle=True)
    body = small or "<b>I am here.</b>\nTap a colorful button — that is the easy path."
    if promo:
        body = f"{body}\n\n{promo}"
    return TalkReply(text=body, pose="present", source="seed-smalltalk")


def _promo_line(chat_id: str, *, sprinkle: bool) -> str:
    promo = active_promo()
    if not promo:
        return ""
    if sprinkle and abs(hash(f"promo:{chat_id}")) % 5:
        return ""
    return f"<b>Staff-approved note</b>\n{promo['headline']}\n{promo['body']}"


def _llm_reply(message: str, hits: list[dict[str, Any]]) -> TalkReply | None:
    context = "\n\n".join(f"[{row['kind']}] {row['title']}: {row['text']}" for row in hits) or "No extra snippets."
    promo = active_promo()
    promo_block = (
        f"Approved promotion: {promo['headline']} — {promo['body']}"
        if promo
        else "No approved promotion. Do not mention a sale, discount, or deal."
    )
    system = (
        f"You are {AGENT_NAME}, the TrueHold Wellness Telegram concierge. "
        "Warm, brief, playful, never sad or dry. One short HTML <b> heading plus a few lines. "
        "Use ONLY the approved context. If it is not there, say you will fetch a person via Team "
        "and offer the tap-menu. Never give dosing, reconstitution, injection, or medical advice. "
        "Never invent products, prices, or sales. Never include http links. "
        "Las Vegas residents, dry vials only, educational only. Under 500 characters."
    )
    user = f"Approved context:\n{context}\n\n{promo_block}\n\nCustomer: {message}"
    try:
        content = _chat(system, user)
    except Exception:
        return None
    if not content or _BLOCK.search(content) or "http" in content.lower():
        return None
    pose = "think" if hits and hits[0]["kind"] in {"policy", "product"} else "present"
    return TalkReply(text=content.strip(), pose=pose, source="llm")


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
