from wellness_agent.catalog import products
from wellness_agent.knowledge import retrieve, seed_approved_knowledge
from wellness_agent.knowledge.house import (
    FASTING_OPENER,
    format_prep_caption,
    host_bio,
    house_experience,
    load_house,
    peptide_record,
    seed_rows,
)
from wellness_agent.knowledge.talk import reply
from wellness_agent.menu import after_pick_keyboard, handle_menu_callback
from wellness_agent.team import member_ids, set_favorite


def test_house_db_covers_every_host_and_sku():
    house = load_house()
    assert "50 years" in house_experience().lower() or "fifty" in house_experience().lower() or "50" in house_experience()
    assert "clinical" in house_experience().lower()
    assert "surgical" in house_experience().lower()
    ids = member_ids()
    bios = house["bios"]
    assert set(bios) == set(ids)
    for member_id in ids:
        row = host_bio(member_id)
        assert row["bio"]
        assert row["herbs"]
        assert "reconstitut" not in row["bio"].lower()
        assert "inject" not in row["bio"].lower()
    sku_ids = {item["id"] for item in products()}
    assert set(house["peptides"]) == sku_ids
    for item in products():
        rec = peptide_record(item["id"])
        assert rec["opener"]
        assert rec["prep"]
        caption = format_prep_caption(item)
        assert len(caption) <= 1024
        assert "reconstitut" not in caption.lower()
        assert "units =" not in caption.lower()
        assert "http" not in caption.lower()
    tirz = peptide_record("tirzepatide")
    reta = peptide_record("retatrutide")
    assert tirz["weight_loss"] and reta["weight_loss"]
    assert tirz["opener"] == FASTING_OPENER
    assert reta["opener"] == FASTING_OPENER
    assert "fast" in FASTING_OPENER.lower()
    assert "either way" in FASTING_OPENER.lower() or "no pressure" in FASTING_OPENER.lower()


def test_house_seed_has_no_mix_math():
    blob = " ".join(text for _id, _kind, _title, text in seed_rows()).lower()
    assert "reconstitut" not in blob
    assert "units =" not in blob
    assert "bac water" not in blob
    assert "http" not in blob
    assert "ginger" in blob
    assert "fasting" in blob


def test_talk_who_are_you_returns_current_host_bio():
    set_favorite("bio-chat", "sage")
    spoken = reply("who are you", chat_id="bio-chat")
    assert spoken.source == "seed-bio"
    lower = spoken.text.lower()
    assert "sage" in lower
    assert "50" in lower or "clinical" in lower
    assert "reconstitut" not in lower


def test_talk_fasting_and_herbs_come_from_the_house_db():
    seed_approved_knowledge()
    fast = reply("what is intermittent fasting", chat_id="fast-chat")
    assert "fast" in fast.text.lower()
    assert FASTING_OPENER.split("?")[0].lower() in fast.text.lower() or "eating window" in fast.text.lower()
    herb = reply("ginger tea for my stomach", chat_id="herb-chat")
    assert herb.source == "seed-herb"
    assert "ginger" in herb.text.lower()
    hits = retrieve("tirzepatide fasting")
    kinds = {row["kind"] for row in hits}
    assert kinds & {"prep", "fasting", "product"}


def test_weight_loss_tile_asks_if_you_have_fasted():
    tg = _FakeTelegramMenu()
    result = handle_menu_callback(
        {
            "id": "t1",
            "data": "w:tile:tirzepatide",
            "from": {"id": 88},
            "message": {"chat": {"id": 88, "type": "private"}},
        },
        tg,
    )
    assert result["action"] == "tile"
    photos = [item for item in tg.sent if "photo" in item]
    caption = photos[-1]["caption"]
    assert FASTING_OPENER in caption
    labels = [btn["text"] for row in photos[-1]["reply_markup"]["inline_keyboard"] for btn in row]
    assert any("yes" in label.lower() for label in labels)
    assert any("not yet" in label.lower() for label in labels)
    markup = after_pick_keyboard("tirzepatide")
    data = [btn.get("callback_data") for row in markup["inline_keyboard"] for btn in row]
    assert "w:fast:tirzepatide:yes" in data
    follow = handle_menu_callback(
        {
            "id": "t2",
            "data": "w:fast:tirzepatide:no",
            "from": {"id": 88},
            "message": {"chat": {"id": 88, "type": "private"}},
        },
        tg,
    )
    assert follow["action"] == "fast"
    assert follow["fasted"] is False
    note = [item["caption"] for item in tg.sent if "photo" in item][-1]
    assert "fast" in note.lower()
    assert "reconstitut" not in note.lower()


class _FakeTelegramMenu:
    def __init__(self) -> None:
        self.sent = []
        self.callbacks = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.sent.append({"text": text, "reply_markup": reply_markup})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append({"photo": str(path), "caption": caption, "reply_markup": reply_markup})
        return {"ok": True}

    def send_document(self, chat_id, path, caption="", reply_markup=None, filename=None, parse_mode=None, message_effect_id=None):
        self.sent.append({"document": str(path), "caption": caption, "reply_markup": reply_markup})
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        self.callbacks.append(callback_query_id)
        return {"ok": True}
