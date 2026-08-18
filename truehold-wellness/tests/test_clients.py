from wellness_agent.clients import client_phone, parse_phone, save_client_phone
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []

    def send_message(self, chat_id, text, reply_markup=None):
        self.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        return {"ok": True}

    def send_document(self, chat_id, path, caption=""):
        self.sent.append({"chat_id": chat_id, "document": str(path), "caption": caption})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None):
        self.sent.append({"chat_id": chat_id, "photo": str(path), "caption": caption})
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        return {"ok": True}


def test_parse_phone_normalizes_us_numbers():
    assert parse_phone("702-555-0100") == "+17025550100"
    assert parse_phone("1 (702) 555-0100") == "+17025550100"
    assert parse_phone("hi") is None


def test_telegram_contact_is_stored():
    tg = _FakeTelegram()
    result = handle_telegram_update(
        {
            "message": {
                "chat": {"id": 33, "type": "private"},
                "from": {"id": 33, "first_name": "Pat"},
                "contact": {"phone_number": "7025550199", "user_id": 33, "first_name": "Pat"},
            }
        },
        tg,
    )
    assert result["action"] == "phone-saved"
    assert client_phone("33") == "+17025550199"
    assert any("17025550199" in (item.get("text") or "") for item in tg.sent)


def test_typed_phone_is_stored_when_telegram_cannot_share():
    tg = _FakeTelegram()
    handle_telegram_update(
        {"message": {"text": "hello", "chat": {"id": 34}, "from": {"id": 34}}},
        tg,
    )
    typed = handle_telegram_update(
        {"message": {"text": "702-555-0188", "chat": {"id": 34}, "from": {"id": 34}}},
        tg,
    )
    assert typed["action"] == "phone-saved"
    assert client_phone("34") == "+17025550188"


def test_order_without_phone_asks_then_completes_after_share():
    tg = _FakeTelegram()
    need = handle_telegram_update(
        {
            "callback_query": {
                "id": "c1",
                "data": "w:yes:klow:1",
                "from": {"id": 35},
                "message": {"chat": {"id": 35, "type": "private"}},
            }
        },
        tg,
    )
    assert need["action"] == "need-phone"
    assert client_phone("35") is None
    done = handle_telegram_update(
        {
            "message": {
                "chat": {"id": 35, "type": "private"},
                "from": {"id": 35},
                "contact": {"phone_number": "7025550177", "user_id": 35, "first_name": "Lee"},
            }
        },
        tg,
    )
    assert done["action"] == "phone-saved"
    assert done["pending"]["action"] == "order-confirm"
    assert client_phone("35") == "+17025550177"
