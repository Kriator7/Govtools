from app.config import Settings
from app.services.sms.relay import resolve_sms_destination


def test_sms_relay_sends_to_operator_phone():
    settings = Settings(sms_relay_mode=True, sms_relay_to="+17025550100", sms_provider="mock")
    dest = resolve_sms_destination("+13109865887", settings)
    assert dest["to"] == "+17025550100"
    assert dest["intended_recipient"] == "+13109865887"
    assert dest["relay_mode"] == "on"


def test_live_twilio_without_relay_number_is_blocked():
    settings = Settings(sms_relay_mode=True, sms_relay_to=None, sms_provider="twilio")
    dest = resolve_sms_destination("+17025550199", settings)
    assert dest["to"] is None
    assert dest["relay_mode"] == "blocked"


def test_mock_sms_without_relay_number_uses_intended():
    settings = Settings(sms_relay_mode=True, sms_relay_to=None, sms_provider="mock")
    dest = resolve_sms_destination("+15555550100", settings)
    assert dest["to"] == "+15555550100"
