from email.message import EmailMessage
from pathlib import Path

from app.config import PROJECT_ROOT
from app.models.investor import Investor
from app.models.realtor import Realtor
from app.models.realtor_packet import RealtorPacket
from app.services.inbox.apply import PacketIntakeService
from app.services.inbox.classify import is_packet_candidate
from app.services.inbox.message import parse_rfc822
from app.services.inbox.redact import redact_text
from app.services.seed import DAMIAN_NAME, TEST_REALTOR_NAME, seed_realtor, upsert_damian_realtor


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
