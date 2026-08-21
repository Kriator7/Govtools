from app.integrations.telegram.mock import MockTelegramProvider
from app.models.realtor_packet import RealtorPacket
from app.services.inbox.las_vegas_idx import PACKET_2_FROM_CAT
from app.services.seed import DAMIAN_NAME, upsert_damian_realtor
from app.services.telegram.idx_ask import apply_idx_reply, parse_idx_reply
from app.services.telegram.inbound import process_telegram_update
from app.utilities.ids import next_public_id


def test_parse_option_3_and_agent_id():
    parsed = parse_idx_reply("Option 3 yes\nMLS agent ID: 445566\nCoverage: LV Henderson Active")
    assert parsed["has_idx"] is True
    assert parsed["chosen_idx_option"] == "3"
    assert parsed["mls_agent_id"] == "445566"
    assert parsed["listing_statuses"] == "active"


def test_parse_damian_mls_agent_id_241888():
    parsed = parse_idx_reply("Damians MLS agent id is 241888")
    assert parsed["has_idx"] is True
    assert parsed["mls_agent_id"] == "241888"
    assert parsed["chosen_idx_option"] is None


def test_yes_on_idx_ask_thread_means_option_3():
    parsed = parse_idx_reply("Yes", reply_to="Packet 2 — live MLS for Agent Real. Trestle WebAPI")
    assert parsed["chosen_idx_option"] == "3"
    assert parse_idx_reply("Yes")["has_idx"] is False


def test_option_2_does_not_feed_the_agent(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    upsert_damian_realtor(db, {"name": DAMIAN_NAME})
    result = apply_idx_reply(db, text="option 2 plugin is fine")
    assert result["applied"] is True
    assert result["feeds_this_agent"] is False
    assert "usable_idx_option_3" in result["missing_fields"]
    assert "does not feed this agent" in result["reply"]


def test_damian_telegram_option_3_updates_packet_2(db, realtor, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    damian = upsert_damian_realtor(db, {"name": DAMIAN_NAME})
    seed = RealtorPacket(
        public_id=next_public_id(db, "PKT"),
        realtor_id=damian.id,
        packet_number=2,
        message_id="<cat-yee-idx@test>",
        payload=dict(PACKET_2_FROM_CAT),
        missing_fields=["chosen_idx_option", "mls_agent_id"],
        status="partial",
    )
    db.add(seed)
    db.flush()
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "message": {
                "text": "Option 3 yes. MLS agent ID: 778899. LV NLV Henderson, Active only.",
                "chat": {"id": -5372586958, "type": "group"},
                "from": {"id": 7592412078, "username": "damianlasvegas"},
            }
        },
        telegram=telegram,
    )
    assert result["action"] == "idx_choice"
    db.refresh(damian)
    assert damian.mls_config_ref == "secret:mls-trestle-pending"
    row = (
        db.query(RealtorPacket)
        .filter(RealtorPacket.realtor_id == damian.id, RealtorPacket.packet_number == 2)
        .order_by(RealtorPacket.updated_at.desc())
        .first()
    )
    assert row.payload["chosen_idx_option"] == "3"
    assert row.payload["mls_agent_id"] == "778899"
    assert "chosen_idx_option" not in (row.missing_fields or [])
    reply = telegram.sent[0]["text"]
    assert reply.startswith("Thank you, Damian. Option 3 is recorded.")
    assert "option 3" in reply.lower()
    assert "778899" in reply
    assert "will not scrape" in reply.lower()
    assert realtor.name != DAMIAN_NAME


def test_option_3_yes_thanks_damian_and_keeps_mls_id_241888(db, realtor, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    damian = upsert_damian_realtor(db, {"name": DAMIAN_NAME})
    damian.mls_config_ref = "pending:las-vegas-realtors-idx-choice"
    seed = RealtorPacket(
        public_id=next_public_id(db, "PKT"),
        realtor_id=damian.id,
        packet_number=2,
        message_id="<cat-yee-idx@test>",
        payload={**PACKET_2_FROM_CAT, "mls_agent_id": "241888"},
        missing_fields=["chosen_idx_option"],
        status="partial",
    )
    db.add(seed)
    db.flush()
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    result = process_telegram_update(
        db,
        realtor,
        {
            "message": {
                "text": "Option 3 yes",
                "chat": {"id": -5372586958, "type": "group"},
                "from": {"id": 7592412078, "username": "damianlasvegas"},
            }
        },
        telegram=telegram,
    )
    assert result["action"] == "idx_choice"
    db.refresh(damian)
    assert damian.mls_config_ref == "secret:mls-trestle-pending"
    row = (
        db.query(RealtorPacket)
        .filter(RealtorPacket.realtor_id == damian.id, RealtorPacket.packet_number == 2)
        .order_by(RealtorPacket.updated_at.desc())
        .first()
    )
    assert row.payload["chosen_idx_option"] == "3"
    assert row.payload["mls_agent_id"] == "241888"
    assert "chosen_idx_option" not in (row.missing_fields or [])
    assert "mls_agent_id" not in (row.missing_fields or [])
    reply = telegram.sent[0]["text"]
    assert reply.startswith("Thank you, Damian. Option 3 is recorded.")
    assert "241888" in reply
    assert "Still need" not in reply
    assert "will not scrape" in reply.lower()
