from app.integrations.email.imap_client import ImapAccount
from app.models.realtor import Realtor
from app.models.realtor_packet import RealtorPacket
from app.services.inbox.message import InboundMessage, parse_rfc822
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
