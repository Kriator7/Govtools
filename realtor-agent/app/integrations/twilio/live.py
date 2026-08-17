"""Twilio Messages create. Credentials must come from Secret Manager / env."""

from typing import Any

import httpx

from app.integrations.twilio.base import SMSProvider


class LiveSMSProvider(SMSProvider):
    name = "twilio"

    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        if not account_sid or not auth_token or not from_number:
            raise ValueError("Twilio credentials are required for live SMS")
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    def send_sms(self, to: str, body: str) -> dict[str, Any]:
        # https://www.twilio.com/docs/sms/api/message-resource#create-a-message-resource
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        with httpx.Client(timeout=20) as client:
            response = client.post(
                url,
                data={"To": to, "From": self.from_number, "Body": body},
                auth=(self.account_sid, self.auth_token),
            )
            response.raise_for_status()
            data = response.json()
        return {"provider_message_id": data.get("sid"), "raw": data, "status": data.get("status")}

    def health(self) -> tuple[str, str]:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}.json"
            with httpx.Client(timeout=10) as client:
                response = client.get(url, auth=(self.account_sid, self.auth_token))
                response.raise_for_status()
            return ("ok", "twilio account lookup succeeded")
        except Exception as exc:  # noqa: BLE001
            return ("error", str(exc))
