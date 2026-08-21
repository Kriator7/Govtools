from app.integrations.email.imap_client import ImapAccount
from app.integrations.telegram.mock import MockTelegramProvider
from app.models.realtor import Realtor
from app.models.realtor_packet import RealtorPacket
from app.services.inbox.classify import is_packet_candidate
from app.services.inbox.message import InboundMessage, parse_rfc822
from app.services.inbox.mls_access import is_mls_api_access_mail
from app.services.inbox.watch import InboxWatchService, configured_imap_accounts
from app.services.seed import DAMIAN_NAME, seed_realtor


class FakeSource:
    def __init__(self, messages: list[InboundMessage]) -> None:
        self.messages = messages
        self.calls: list[str] = []

    def fetch(self, account: ImapAccount, *, lookback_days: int) -> list[InboundMessage]:
        self.calls.append(account.username)
        return list(self.messages)


def _damian_msg() -> InboundMessage:
    from email.message import EmailMessage

    message = EmailMessage()
    message["From"] = "Damian Einbinder <damian@homefinderrealty.example>"
    message["To"] = "jrupe7@gmail.com"
    message["Subject"] = "Packet 1"
    message["Message-ID"] = "<packet-1-watch@test.example>"
    message.set_content(
        "Packet 1\nFull legal name: Damian Einbinder\nBrokerage: Home Finder Realty\n"
        "Nevada license number: S.1\nMobile phone: +17025550000\nWork email: damian@homefinderrealty.example\n"
        "Timezone: Pacific\n"
    )
    return parse_rfc822(message.as_bytes(), account="jrupe7@gmail.com", uid="10")


def test_watch_applies_new_mail_once(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    monkeypatch.setenv("EMAIL_SMTP_USERNAME", "cardanomint@gmail.com")
    monkeypatch.setenv("EMAIL_SMTP_PASSWORD", "xxxx xxxx xxxx xxxx")
    monkeypatch.setenv("IMAP_USERNAME", "jrupe7@gmail.com")
    monkeypatch.setenv("IMAP_PASSWORD", "")
    from app.config import get_settings

    get_settings.cache_clear()
    seed_realtor(db)
    source = FakeSource([_damian_msg()])
    watcher = InboxWatchService(db, get_settings(), source=source)
    first = watcher.poll_once()
    second = watcher.poll_once()
    assert first["processed"][0]["status"] == "applied"
    assert second["skipped"] >= 1
    assert db.query(Realtor).filter(Realtor.name == DAMIAN_NAME).count() == 1
    assert db.query(RealtorPacket).count() == 1


def test_configured_accounts_skip_jrupe7_without_password(monkeypatch):
    monkeypatch.setenv("IMAP_USERNAME", "jrupe7@gmail.com")
    monkeypatch.setenv("IMAP_PASSWORD", "")
    monkeypatch.setenv("JRUPE7_IMAP_PASSWORD", "")
    monkeypatch.setenv("EMAIL_SMTP_USERNAME", "cardanomint@gmail.com")
    monkeypatch.setenv("EMAIL_SMTP_PASSWORD", "abcdefghijklmnop")
    from app.config import get_settings

    get_settings.cache_clear()
    accounts = configured_imap_accounts(get_settings())
    assert [item.username for item in accounts] == ["cardanomint@gmail.com"]


def test_configured_accounts_include_jrupe7_when_password_set(monkeypatch):
    monkeypatch.setenv("IMAP_USERNAME", "jrupe7@gmail.com")
    monkeypatch.setenv("IMAP_PASSWORD", "sixteencharspass")
    monkeypatch.setenv("EMAIL_SMTP_USERNAME", "cardanomint@gmail.com")
    monkeypatch.setenv("EMAIL_SMTP_PASSWORD", "abcdefghijklmnop")
    from app.config import get_settings

    get_settings.cache_clear()
    accounts = configured_imap_accounts(get_settings())
    assert [item.username for item in accounts] == ["jrupe7@gmail.com", "cardanomint@gmail.com"]


def _rfc822_msg(*, sender: str, subject: str, body: str, message_id: str) -> InboundMessage:
    from email.message import EmailMessage

    message = EmailMessage()
    message["From"] = sender
    message["To"] = "jrupe7@gmail.com"
    message["Subject"] = subject
    message["Message-ID"] = message_id
    message.set_content(body)
    return parse_rfc822(message.as_bytes(), account="jrupe7@gmail.com", uid="99")


def test_trestle_access_mail_is_packet_candidate_and_not_idx_options():
    access = _rfc822_msg(
        sender="Trestle Support <trestlesupport@cotality.com>",
        subject="Add MLO Connection — Las Vegas REALTORS",
        body="Please sign the data license and add an MLO connection for your technology provider account.",
        message_id="<trestle-mlo@test.example>",
    )
    assert is_packet_candidate(access) is True
    assert is_mls_api_access_mail(access) is True
    options = _rfc822_msg(
        sender='Catalino "Cat" Yee <idx@lasvegasrealtors.example>',
        subject="IDX options for your website",
        body="Here are the following options for obtaining IDX for your website. Do NOT choose 2 and 3 together.",
        message_id="<cat-idx@test.example>",
    )
    assert is_packet_candidate(options) is True
    assert is_mls_api_access_mail(options) is False


def test_watch_alerts_telegram_for_trestle_access_mail(db, tmp_path, monkeypatch):
    monkeypatch.setenv("INBOX_STORAGE_PATH", str(tmp_path / "inbox"))
    monkeypatch.setenv("EMAIL_SMTP_USERNAME", "")
    monkeypatch.setenv("EMAIL_SMTP_PASSWORD", "")
    monkeypatch.setenv("IMAP_USERNAME", "jrupe7@gmail.com")
    monkeypatch.setenv("IMAP_PASSWORD", "sixteencharspass")
    monkeypatch.setenv("TELEGRAM_MODE", "mock")
    monkeypatch.setenv("TELEGRAM_OPERATOR_CHAT_ID", "-5372586958")
    from app.config import get_settings

    get_settings.cache_clear()
    seed_realtor(db)
    access = _rfc822_msg(
        sender="Trestle Support <trestlesupport@cotality.com>",
        subject="Your Trestle API credentials",
        body="Client ID: abc123\nClient Secret: super-secret-value\nAdd MLO connection for Las Vegas REALTORS.",
        message_id="<trestle-creds@test.example>",
    )
    telegram = MockTelegramProvider(outbox_path=tmp_path / "tg.json")
    watcher = InboxWatchService(db, get_settings(), source=FakeSource([access]), telegram=telegram)
    result = watcher.poll_once()
    applied = result["processed"][0]
    assert applied["status"] in {"applied", "partial"}
    assert applied["mls_access_alert"]["sent"] is True
    reply = telegram.sent[0]["text"]
    assert "MLS API access mail arrived" in reply
    assert "super-secret-value" not in reply
    assert "will not scrape" in reply.lower()
    assert "will not text Damian" in reply
    assert len(telegram.sent) == 1
