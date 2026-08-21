from email.message import EmailMessage
from pathlib import Path

from app.config import PROJECT_ROOT
from app.models.investor import Investor
from app.models.realtor import Realtor
from app.models.realtor_packet import RealtorPacket
from app.services.inbox.apply import PacketIntakeService
from app.services.inbox.classify import is_calendar_noise, is_damian_sender, is_packet_candidate
from app.services.inbox.message import parse_rfc822
from app.services.inbox.redact import redact_text
from app.services.seed import DAMIAN_EMAIL, DAMIAN_NAME, TEST_REALTOR_NAME, seed_realtor, upsert_damian_realtor


PACKET_1_BODY = """Packet 1 — Who you are

Full legal name: Damian Einbinder
Brokerage: Home Finder Realty
Nevada license number: S.00654321
License expiration: 2027-12-31
Mobile phone: +17025551999
Work email: damian@homefinderrealty.example
Timezone: Pacific
Side: both
"""

PACKET_5_BODY = """Packet 5

I will use Telegram as the command center: Yes
Telegram username: @HomeFinderDamian
Hours we may alert: 7:00 a.m. – 8:00 p.m. Pacific, seven days
Minimum match score: 80+
Re-alert on price drops: Yes
Back on market: Yes
MLS password: hunter2
"""


def _rfc822(*, sender: str, to: str, subject: str, body: str, attachments: list[tuple[str, str, bytes]] | None = None) -> bytes:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message["Message-ID"] = f"<{subject.replace(' ', '-').lower()}@test.example>"
    message.set_content(body)
    for filename, content_type, data in attachments or []:
        maintype, _, subtype = content_type.partition("/")
        message.add_attachment(data, maintype=maintype or "application", subtype=subtype or "octet-stream", filename=filename)
    return message.as_bytes()


def test_packet_1_creates_damian_without_clobbering_test_operator(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    test_realtor = seed_realtor(db)
    raw = _rfc822(
        sender="Damian Einbinder <damian@homefinderrealty.example>",
        to="jrupe7@gmail.com",
        subject="Packet 1",
        body=PACKET_1_BODY,
    )
    inbound = parse_rfc822(raw, account="jrupe7@gmail.com", uid="1")
    result = PacketIntakeService(db).apply_message(inbound)
    db.commit()
    assert result["status"] == "applied"
    damian = db.query(Realtor).filter(Realtor.name == DAMIAN_NAME).one()
    assert damian.brokerage == "Home Finder Realty"
    assert damian.license_number == "S.00654321"
    assert damian.email == "damian@homefinderrealty.example"
    assert damian.phone == "+17025551999"
    assert damian.timezone == "America/Los_Angeles"
    assert test_realtor.name == TEST_REALTOR_NAME
    seed_realtor(db)
    db.refresh(damian)
    assert damian.name == DAMIAN_NAME
    assert db.query(Realtor).filter(Realtor.name == TEST_REALTOR_NAME).count() == 1
    packet = db.query(RealtorPacket).filter(RealtorPacket.packet_number == 1).one()
    assert packet.status == "applied"
    assert not packet.missing_fields


def test_packet_3_and_4_import_investors_onto_damian(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    seed_realtor(db)
    csv_bytes = (PROJECT_ROOT / "data" / "imports" / "sample_investors.csv").read_bytes()
    raw = _rfc822(
        sender="Damian Einbinder <de@homefinderrealty.example>",
        to="James Rupe <jrupe7@gmail.com>",
        subject="Packet 3 investor list and Packet 4 buy boxes",
        body="Spreadsheet attached.",
        attachments=[("investors.csv", "text/csv", csv_bytes)],
    )
    inbound = parse_rfc822(raw, account="jrupe7@gmail.com", uid="2")
    result = PacketIntakeService(db).apply_message(inbound)
    db.commit()
    damian = db.query(Realtor).filter(Realtor.name == DAMIAN_NAME).one()
    investors = db.query(Investor).filter(Investor.realtor_id == damian.id).all()
    names = {item.name for item in investors}
    assert "ABC Capital" in names
    assert "Desert Peak Investments" in names
    packets = {item["packet"] for item in result["packets"]}
    assert 3 in packets and 4 in packets


def test_packet_5_merges_alerts_and_redacts_passwords(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    raw = _rfc822(
        sender="Damian Einbinder <damian@homefinderrealty.example>",
        to="jrupe7@gmail.com",
        subject="Re: Packet 5",
        body=PACKET_5_BODY,
    )
    inbound = parse_rfc822(raw, account="jrupe7@gmail.com", uid="3")
    PacketIntakeService(db).apply_message(inbound)
    db.commit()
    damian = db.query(Realtor).filter(Realtor.name == DAMIAN_NAME).one()
    assert damian.telegram_user_id == "@HomeFinderDamian"
    assert damian.notification_settings["alert_min_score"] == 80
    assert damian.notification_settings["realert_price_drop"] is True
    stored = (tmp_path / "inbox").rglob("body.txt")
    body = next(stored).read_text(encoding="utf-8")
    assert "hunter2" not in body
    assert "[REDACTED]" in body or "not stored" in body
    assert "hunter2" not in redact_text(PACKET_5_BODY)


def test_zillow_and_unrelated_mail_are_ignored(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    zillow = parse_rfc822(
        _rfc822(
            sender="Zillow <alerts@zillow.com>",
            to="jrupe7@gmail.com",
            subject="New listing in Las Vegas",
            body="A house listed. Do not scrape.",
        ),
        account="jrupe7@gmail.com",
        uid="4",
    )
    random_csv = parse_rfc822(
        _rfc822(
            sender="Spam <noreply@meetup.com>",
            to="jrupe7@gmail.com",
            subject="investor list",
            body="not damian",
            attachments=[("investors.csv", "text/csv", b"Investor Name\nNope\n")],
        ),
        account="jrupe7@gmail.com",
        uid="5",
    )
    assert not is_packet_candidate(zillow, "jrupe7@gmail.com")
    result = PacketIntakeService(db).apply_message(zillow)
    assert result["status"] == "ignored"
    result = PacketIntakeService(db).apply_message(random_csv)
    assert result["status"] == "ignored"
    assert db.query(Realtor).filter(Realtor.name == DAMIAN_NAME).count() == 0


def test_upsert_damian_does_not_reuse_test_operator(db):
    test = seed_realtor(db)
    damian = upsert_damian_realtor(db, {"name": DAMIAN_NAME, "email": test.email})
    assert damian.id != test.id
    assert damian.name == DAMIAN_NAME


def test_binder_thehomefinderlv_sender_is_applied(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    raw = _rfc822(
        sender=f"Home Finder LV <{DAMIAN_EMAIL}>",
        to="jrupe7@gmail.com",
        subject="Re: document packet",
        body=PACKET_1_BODY.replace("damian@homefinderrealty.example", DAMIAN_EMAIL),
    )
    inbound = parse_rfc822(raw, account="jrupe7@gmail.com", uid="6")
    assert is_damian_sender(inbound)
    result = PacketIntakeService(db).apply_message(inbound)
    db.commit()
    assert result["status"] == "applied"
    damian = db.query(Realtor).filter(Realtor.email == DAMIAN_EMAIL).one()
    assert damian.name == DAMIAN_NAME
    assert damian.license_number == "S.00654321"


def test_cat_yee_idx_email_is_packet_2_partial_and_not_live_mls(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    body = (PROJECT_ROOT / "data" / "imports" / "packet2_las_vegas_realtors_idx.txt").read_text(encoding="utf-8")
    raw = _rfc822(
        sender='Catalino "Cat" Yee <idx@lasvegasrealtors.example>',
        to="jrupe7@gmail.com",
        subject="IDX options for your website",
        body=body,
    )
    inbound = parse_rfc822(raw, account="pasted", uid="7")
    result = PacketIntakeService(db).apply_message(inbound)
    db.commit()
    assert result["status"] == "partial"
    packets = {item["packet"] for item in result["packets"]}
    assert packets == {2}
    row = db.query(RealtorPacket).filter(RealtorPacket.packet_number == 2).one()
    assert row.payload["mls_name"] == "Las Vegas REALTORS MLS (Matrix)"
    assert row.payload["idx_option_3"] == "Trestle WebAPI data feed"
    assert row.payload["idx_rule"].startswith("Do NOT choose")
    assert not row.payload.get("chosen_idx_option")
    assert "chosen_idx_option" in row.missing_fields
    assert "mls_agent_id" in row.missing_fields
    damian = db.query(Realtor).filter(Realtor.name == DAMIAN_NAME).one()
    assert damian.mls_config_ref == "pending:las-vegas-realtors-idx-choice"


PACKET_1_NUMBERED = """Packet 1

1. Damian Einbinder
2. Home Finder Realty
3. B.0148654 exp 7/31/2027
4. Damian Einbinder B.0148654 (broker-owner)
5. 9890 S Maryland Pkwy 200a Las Vegas, NV 89183
6. 702-371-0950
7. binder@thehomefinderlv.com
8. Pacific
9. Buyer side

On Wed, Aug 19, 2026 at 9:00 AM James wrote:
Full legal name:
Brokerage legal name:
"""


def test_numbered_packet_1_from_damian_reply(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    raw = _rfc822(
        sender=f"Damian Einbinder Realtor <{DAMIAN_EMAIL}>",
        to="jrupe7@gmail.com",
        subject="Re: Packet 1 — Who you are",
        body=PACKET_1_NUMBERED,
    )
    inbound = parse_rfc822(raw, account="jrupe7@gmail.com", uid="8")
    result = PacketIntakeService(db).apply_message(inbound)
    db.commit()
    assert result["status"] == "applied"
    damian = db.query(Realtor).filter(Realtor.name == DAMIAN_NAME).one()
    assert damian.license_number == "B.0148654"
    assert damian.phone == "+17023710950"
    assert damian.email == DAMIAN_EMAIL
    assert damian.timezone == "America/Los_Angeles"
    assert "9890 S Maryland Pkwy" in (damian.notes or "")
    packet = db.query(RealtorPacket).filter(RealtorPacket.packet_number == 1).one()
    assert packet.payload["side"].lower().startswith("buyer")
    assert packet.payload["license_expiration"] == "7/31/2027"


def test_calendar_accept_is_ignored(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    raw = _rfc822(
        sender="Damian Einbinder <binder@thehomefinderlv.com>",
        to="jrupe7@gmail.com",
        subject="Accepted: Packet 4 buy boxes",
        body="Damian Einbinder has accepted this invitation.\n\nNotes: discuss buy boxes.",
    )
    inbound = parse_rfc822(raw, account="jrupe7@gmail.com", uid="9")
    assert is_calendar_noise(inbound)
    assert not is_packet_candidate(inbound, "jrupe7@gmail.com")
    result = PacketIntakeService(db).apply_message(inbound)
    assert result["status"] == "ignored"
    assert db.query(RealtorPacket).count() == 0


def test_packet_4_note_overlays_80_pct_on_damian_not_test_operator(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from decimal import Decimal

    from app.config import get_settings
    from app.models.investor import Investor
    from app.models.investor_criteria import InvestorCriteria
    from app.utilities.ids import next_public_id

    get_settings.cache_clear()
    test = seed_realtor(db)
    test_investor = db.query(Investor).filter(Investor.realtor_id == test.id).one_or_none()
    if test_investor is None:
        test_investor = Investor(
            public_id=next_public_id(db, "INV"),
            realtor_id=test.id,
            name="ABC Capital",
            preferred_channel="sms",
            communication_permissions={"sms": True, "email": True},
        )
        db.add(test_investor)
        db.flush()
        db.add(
            InvestorCriteria(
                public_id=next_public_id(db, "CRT"),
                realtor_id=test.id,
                investor_id=test_investor.id,
                name="Henderson multifamily value-add",
                max_price_pct_of_arv=Decimal("0.9000"),
                min_price=Decimal("400000"),
                max_price=Decimal("1200000"),
            )
        )
        db.flush()
    damian = upsert_damian_realtor(db, {"name": DAMIAN_NAME, "email": DAMIAN_EMAIL})
    pirates = Investor(
        public_id=next_public_id(db, "INV"),
        realtor_id=damian.id,
        name="Pirates IG LLC",
        contact_name="Amos",
        phone="+15555550199",
        email="amos@example.test",
        preferred_channel="phone",
        communication_permissions={"sms": False, "email": False},
    )
    db.add(pirates)
    db.flush()
    profile = InvestorCriteria(
        public_id=next_public_id(db, "CRT"),
        realtor_id=damian.id,
        investor_id=pirates.id,
        name="Imported profile",
        property_types=["single_family"],
        hoa_required=False,
        max_price_pct_of_arv=Decimal("0.9000"),
    )
    db.add(profile)
    db.flush()
    raw = _rfc822(
        sender=f"Damian Einbinder <{DAMIAN_EMAIL}>",
        to="jrupe7@gmail.com",
        subject="Re: Packet 4 — Investor buy boxes",
        body=(
            "Currently, the only requirement is 80% of market value, single-family, "
            "and no HOA. Subject to change.\n\nOn Tue, James wrote:\nPacket 4 buy box\n"
        ),
    )
    inbound = parse_rfc822(raw, account="jrupe7@gmail.com", uid="10")
    result = PacketIntakeService(db).apply_message(inbound)
    db.commit()
    db.refresh(profile)
    db.refresh(test_investor)
    test_profile = (
        db.query(InvestorCriteria).filter(InvestorCriteria.investor_id == test_investor.id).first()
    )
    assert result["status"] == "applied"
    assert profile.max_price_pct_of_arv == Decimal("0.80")
    assert profile.property_types == ["single_family"]
    assert profile.hoa_required is False
    assert test_profile is not None
    assert test_profile.max_price_pct_of_arv == Decimal("0.9000")


def test_packet_6_sets_manual_investor_notify(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    from app.config import get_settings

    get_settings.cache_clear()
    raw = _rfc822(
        sender=f"Damian Einbinder <{DAMIAN_EMAIL}>",
        to="jrupe7@gmail.com",
        subject="Re: Packet 6",
        body=(
            "1. Manual communication until the investor is comfortable\n"
            "2. I do not have Twilio\n"
            "3. 702-371-0950\n"
            "4. This one just popped up (address).\n"
            "5. offer xxx\n"
            "6. TBD\n"
            "7. texting and calls must be done manually\n"
        ),
    )
    inbound = parse_rfc822(raw, account="jrupe7@gmail.com", uid="11")
    result = PacketIntakeService(db).apply_message(inbound)
    db.commit()
    damian = db.query(Realtor).filter(Realtor.name == DAMIAN_NAME).one()
    assert damian.notification_settings["investor_notify_mode"] == "manual"
    assert damian.notification_settings["auto_notify_investors"] is False
    assert damian.notification_settings["twilio"] is False
    assert result["status"] == "applied"
