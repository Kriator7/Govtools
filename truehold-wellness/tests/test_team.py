from wellness_agent.inventory.build_agent import POSES, agent_path, crew_source, portrait_path
from wellness_agent.knowledge.talk import reply
from wellness_agent.menu import confirm_keyboard, handle_menu_callback, pick_host_keyboard, quick_menu_keyboard
from wellness_agent.session_store import mark_intro_played
from wellness_agent.team import (
    advance_on_greet,
    button_label,
    button_style,
    current_host,
    effect_id,
    favorite_id,
    get_member,
    member_ids,
    members,
    rotate_again,
    set_favorite,
    skip_to_next,
    tour_complete,
)
from wellness_agent.team.buttons import DEFAULT_BUTTONS, KITS
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []
        self.callbacks = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append(
            {
                "chat_id": chat_id,
                "photo": str(path),
                "caption": caption,
                "reply_markup": reply_markup,
                "message_effect_id": message_effect_id,
            }
        )
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        self.callbacks.append(callback_query_id)
        return {"ok": True}


def _tap(data, chat_id=21, callback_id="host-cb"):
    return {
        "id": callback_id,
        "data": data,
        "from": {"id": chat_id},
        "message": {"chat": {"id": chat_id, "type": "private"}},
    }


def _hi(chat_id=21):
    return {
        "message": {
            "text": "hi",
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id},
        }
    }


def test_floor_team_has_twenty_distinct_hosts():
    rows = members()
    assert len(rows) == 20
    ids = member_ids()
    assert ids[0] == "theo"
    assert len(set(ids)) == 20
    assert len({row["name"] for row in rows}) == 20
    assert len({row["icon"] for row in rows}) == 20
    for row in rows:
        for key in (
            "role",
            "color",
            "button_style",
            "style",
            "hello",
            "present",
            "think",
            "work",
            "cheer",
            "soon",
            "joke",
            "creed",
            "effect",
        ):
            assert row.get(key), f"{row['id']} missing {key}"
        assert str(row["color"]).startswith("#")
        assert row["button_style"] in {"primary", "success", "danger"}
        assert row["effect"] in {"party", "fire", "heart", "thumbs"}
        assert effect_id(row)
        assert row["id"] in KITS
        kit = KITS[row["id"]]
        assert kit["prep"] != DEFAULT_BUTTONS["prep"]
        assert "Prep" in kit["prep"]
        assert "Team" in kit["team"]
        assert "Crew" in kit["crew"]
        blob = " ".join(
            str(row[key])
            for key in ("hello", "present", "think", "work", "cheer", "soon", "joke", "creed")
        ).lower()
        assert "care" in str(row["hello"]).lower() or "health" in str(row["hello"]).lower() or "well" in str(row["hello"]).lower()
        assert len(str(row["creed"])) > 40
        assert "units =" not in blob
        assert "inject" not in blob
        assert "bac water" not in blob
        assert "http" not in blob
    assert len({KITS[row["id"]]["prep"] for row in rows}) == 20


def test_portraits_exist_for_every_host_and_pose():
    for row in members():
        for pose in POSES:
            path = portrait_path(pose, row["id"])
            assert path.is_file(), f"{row['id']}-{pose}"
            assert path.stat().st_size > 1000


def test_host_cards_are_named_for_the_member():
    card = agent_path("present", "mira")
    assert card.name == "mira-present.jpg"
    assert card.is_file()
    assert card.stat().st_size > 1000


def test_rotation_meets_each_host_then_stops():
    chat = "tour-1"
    seen = [advance_on_greet(chat)["id"] for _ in range(20)]
    assert seen == member_ids()
    assert tour_complete(chat)
    assert advance_on_greet(chat)["id"] == member_ids()[-1]


def test_favorite_locks_and_rotate_resets_the_tour():
    chat = "fav-1"
    assert advance_on_greet(chat)["id"] == "theo"
    locked = set_favorite(chat, "vega")
    assert locked["id"] == "vega"
    assert favorite_id(chat) == "vega"
    assert advance_on_greet(chat)["id"] == "vega"
    assert skip_to_next(chat)["id"] == "vega"
    host = rotate_again(chat)
    assert host["id"] == "theo"
    assert favorite_id(chat) is None
    assert advance_on_greet(chat)["id"] == "mira"


def test_greet_again_rotates_hosts_and_can_lock_a_favorite():
    mark_intro_played("21")
    tg = _FakeTelegram()
    first = handle_telegram_update(_hi(21), tg)
    assert first["action"] == "greet-again"
    photo = [item for item in tg.sent if "photo" in item][-1]
    assert "theo-wave.jpg" in photo["photo"]
    assert "Theo" in photo["caption"]
    assert "already live in you" in photo["caption"].lower() or "tools to respect" in photo["caption"].lower()
    assert photo["message_effect_id"]
    labels = [
        btn["text"]
        for row in (photo.get("reply_markup") or {}).get("inline_keyboard") or []
        for btn in row
    ]
    assert any("Favorite Theo" in label for label in labels)
    assert any("Next" in label for label in labels)
    nxt = handle_menu_callback(_tap("w:host:next"), tg)
    assert nxt["action"] == "host-next"
    assert nxt["host"] == "mira"
    mira = [item for item in tg.sent if str(item.get("photo") or "").endswith("mira-wave.jpg")]
    assert mira
    fav = handle_menu_callback(_tap("w:host:set:dash"), tg)
    assert fav == {"ok": True, "action": "host-set", "chat_id": "21", "host": "dash"}
    assert current_host("21")["id"] == "dash"
    tg.sent.clear()
    again = handle_telegram_update(_hi(21), tg)
    assert again["action"] == "greet-again"
    locked = [item for item in tg.sent if "photo" in item][-1]
    assert "dash-wave.jpg" in locked["photo"]
    assert "Dash" in locked["caption"]
    assert any("is yours" in str(locked.get("reply_markup") or "") for _ in [0])


def test_talk_signs_the_current_host_and_still_refuses_dose_math():
    set_favorite("talk-1", "rio")
    spoken = reply("how do I mix NAD+", chat_id="talk-1")
    lower = spoken.text.lower()
    assert "rio" in spoken.text.lower()
    assert "sheet" in lower or "locked" in lower or "pdf" in lower
    assert "reconstitut" not in lower
    assert "units =" not in lower
    assert "http" not in lower


def test_talk_answers_house_creed_in_the_current_host_voice():
    set_favorite("creed-1", "wynn")
    spoken = reply("why do you care about vitamin C and oranges?", chat_id="creed-1")
    lower = spoken.text.lower()
    assert spoken.source == "seed-creed"
    assert "wynn" in spoken.text.lower()
    assert "orange" in lower or "vitamin" in lower
    assert "hostage" in lower or "people" in lower or "access" in lower
    assert "reconstitut" not in lower
    assert "units =" not in lower
    assert "http" not in lower


def test_all_poses_exist_for_theo():
    for pose in POSES:
        assert portrait_path(pose, "theo").is_file()


def test_host_keyboards_use_telegram_button_style():
    """Telegram only allows primary/success/danger — not arbitrary hex.

    https://core.telegram.org/bots/api#inlinekeyboardbutton
    """
    assert button_style({"button_style": "primary"}) == "primary"
    theo = quick_menu_keyboard("style-theo")
    styles = {btn.get("style") for row in theo["inline_keyboard"] for btn in row if btn.get("callback_data", "").startswith("w:tile:")}
    assert styles == {"primary"}
    set_favorite("style-mira", "mira")
    mira = quick_menu_keyboard("style-mira")
    styles = {btn.get("style") for row in mira["inline_keyboard"] for btn in row if btn.get("callback_data", "").startswith("w:tile:")}
    assert styles == {"success"}
    confirm = confirm_keyboard("klow", "1")
    by_text = {btn["text"]: btn.get("style") for row in confirm["inline_keyboard"] for btn in row}
    assert by_text["✅ Vegas"] == "success"
    assert by_text["📍 Not LV"] == "danger"
    picker = pick_host_keyboard(get_member("vega"))
    names = {btn["text"]: btn.get("style") for row in picker["inline_keyboard"] for btn in row}
    assert names["🧬 Mira"] == "success"
    assert names["🌸 Lila"] == "danger"
    assert names[button_label(get_member("vega"), "menu")] == "danger"
    theo = get_member("theo")
    mira = get_member("mira")
    assert button_label(theo, "prep") == "⚡ Prep"
    assert button_label(mira, "prep") == "🧬 Prep"
    assert button_label(None, "prep") == "🛠️ Prep"
    set_favorite("kit-mira", "mira")
    mira_menu = quick_menu_keyboard("kit-mira")
    chrome = [btn["text"] for row in mira_menu["inline_keyboard"] for btn in row]
    assert "🧬 Prep" in chrome
    assert "🥼 Team" in chrome
    assert "🔬 Crew" in chrome
    assert "🛠️ Prep" not in chrome


def test_crew_class_photo_exists():
    path = crew_source()
    assert path.is_file()
    assert path.stat().st_size > 1000


def test_lets_see_the_crew_sends_the_class_photo():
    from wellness_agent.session_store import mark_intro_played

    mark_intro_played("31")
    tg = _FakeTelegram()
    result = handle_telegram_update(
        {
            "message": {
                "text": "lets see the crew",
                "chat": {"id": 31, "type": "private"},
                "from": {"id": 31},
            }
        },
        tg,
    )
    assert result["action"] == "crew"
    photos = [item for item in tg.sent if "photo" in item]
    assert photos
    assert photos[0]["photo"].endswith("crew.jpg")
    assert "floor crew" in (photos[0].get("caption") or "").lower()
    labels = [
        btn["text"]
        for row in (photos[0].get("reply_markup") or {}).get("inline_keyboard") or []
        for btn in row
    ]
    assert any("Crew" in label for label in labels)
    tap = handle_menu_callback(
        {
            "id": "crew-cb",
            "data": "w:crew",
            "from": {"id": 31},
            "message": {"chat": {"id": 31, "type": "private"}},
        },
        tg,
    )
    assert tap["action"] == "crew"
