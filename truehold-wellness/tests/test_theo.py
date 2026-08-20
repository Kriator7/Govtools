from wellness_agent.inventory.build_agent import POSES, agent_path, ensure_agent, portrait_path
from wellness_agent.knowledge import (
    active_promo,
    decide_promo,
    draft_promo,
    retrieve,
    seed_approved_knowledge,
)
from wellness_agent.knowledge.talk import reply
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup, "parse_mode": parse_mode})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append(
            {
                "chat_id": chat_id,
                "photo": str(path),
                "caption": caption,
                "reply_markup": reply_markup,
                "parse_mode": parse_mode,
            }
        )
        return {"ok": True}

    def send_document(self, chat_id, path, caption="", reply_markup=None, filename=None, parse_mode=None):
        self.sent.append({"document": str(path), "caption": caption, "filename": filename})
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        return {"ok": True}


def test_theo_portraits_exist_for_each_pose():
    from wellness_agent.inventory.graphics import tech_hud_overlay

    ensure_agent()
    hud = tech_hud_overlay((200, 120), seed=1)
    assert hud.mode == "RGBA"
    extrema = hud.getextrema()
    assert extrema[-1][1] > 0
    for pose in POSES:
        assert portrait_path(pose).is_file()
        card = agent_path(pose)
        assert card.is_file()
        assert card.stat().st_size > 1000


def test_seed_knowledge_covers_skus_and_no_mix_math_in_product_blurbs():
    seed_approved_knowledge()
    hits = retrieve("semax sheet")
    assert hits
    blob = " ".join(row["text"].lower() for row in hits)
    assert "semax" in blob
    assert "reconstitut" not in blob
    assert "units =" not in blob


def test_talk_stays_on_approved_text_without_llm():
    spoken = reply("how do I mix NAD+", chat_id="1")
    lower = spoken.text.lower()
    assert "sheet" in lower or "locked" in lower or "pdf" in lower
    assert "reconstitut" not in lower
    assert "http" not in lower


def test_pending_promo_is_hidden_until_staff_approve():
    spoken = reply("any sale?", chat_id="sale-chat")
    assert "staff-approved note" not in spoken.text.lower()
    assert "ADPILV2026" in spoken.text
    draft = draft_promo("10% off KLOW", "Las Vegas only this weekend", staff_id="42")
    assert draft["status"] == "pending"
    assert active_promo() is None
    spoken = reply("any sale?", chat_id="sale-chat")
    assert "Las Vegas only this weekend" not in spoken.text
    decide_promo(draft["id"], status="approved", staff_id="42")
    assert active_promo()["headline"] == "10% off KLOW"


def test_staff_promo_commands_and_customer_denied(monkeypatch):
    monkeypatch.setenv("WELLNESS_OPERATOR_USER_IDS", "42")
    staff = _FakeTelegram()
    denied = handle_telegram_update(
        {"message": {"text": "/promo draft Weekend | Las Vegas only", "chat": {"id": 99, "type": "private"}, "from": {"id": 99}}},
        staff,
    )
    assert denied["action"] == "staff-denied"
    tg = _FakeTelegram()
    draft = handle_telegram_update(
        {"message": {"text": "/promo draft Weekend wave | Las Vegas residents only", "chat": {"id": 42, "type": "private"}, "from": {"id": 42}}},
        tg,
    )
    assert draft["action"] == "promo-draft"
    approve = handle_telegram_update(
        {"message": {"text": f"/promo approve {draft['id']}", "chat": {"id": 42, "type": "private"}, "from": {"id": 42}}},
        tg,
    )
    assert approve["action"] == "promo-approved"
    assert active_promo()["headline"] == "Weekend wave"
