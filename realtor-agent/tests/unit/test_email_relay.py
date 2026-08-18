from app.config import Settings
from app.services.email.relay import resolve_email_envelope


def test_relay_sends_to_cardanomint_and_keeps_intended_recipient():
    settings = Settings(
        email_from="cardanomint@gmail.com",
        email_relay_to="cardanomint@gmail.com",
        email_relay_mode=True,
    )
    envelope = resolve_email_envelope("investor@example.invalid", settings)
    assert envelope["from_address"] == "cardanomint@gmail.com"
    assert envelope["to"] == "cardanomint@gmail.com"
    assert envelope["intended_recipient"] == "investor@example.invalid"
    assert envelope["relay_mode"] == "on"


def test_relay_can_be_turned_off_without_code_changes():
    settings = Settings(
        email_from="cardanomint@gmail.com",
        email_relay_to="cardanomint@gmail.com",
        email_relay_mode=False,
    )
    envelope = resolve_email_envelope("investor@example.invalid", settings)
    assert envelope["to"] == "investor@example.invalid"
    assert envelope["from_address"] == "cardanomint@gmail.com"
    assert envelope["relay_mode"] == "off"
