import json
from email.message import EmailMessage

from wellness_agent.cli import main
from wellness_agent.stamp import (
    format_stamp,
    send_stamp_email,
    stamp_payload,
    stamp_subject,
)
from wellness_agent.telegram_inbound import handle_telegram_update


def _write_lots(tmp_path):
    path = tmp_path / "inventory_lots.json"
    path.write_text(
        json.dumps(
            {
                "tracker": {
                    "drive_folder": "https://drive.google.com/drive/folders/tracker",
                    "lots_sheet": "https://docs.google.com/spreadsheets/d/lots",
                    "coa_sheet": "https://docs.google.com/spreadsheets/d/coas",
                    "clients_sheet": "https://docs.google.com/spreadsheets/d/clients",
                    "logs_sheet": "https://docs.google.com/spreadsheets/d/logs",
                },
                "lots": [
                    {
                        "lot_id": "KLOW-TEST",
                        "sku_id": "klow",
                        "name": "KLOW",
                        "strength": "80 mg lyophilized vial",
                        "kits_received": 5,
                        "vials_received": 50,
                        "vials_on_hand": 50,
                        "label_code": "LUMI593-A62",
                        "label_lot": "LOT-Z51-Z12",
                        "coa_lot": "CPC260728KLOW",
                        "coa_id": "CPC260728KLOW",
                        "status": "in_stock",
                    }
                ],
                "coas": [],
            }
        ),
        encoding="utf-8",
    )


def _write_roster(tmp_path):
    path = tmp_path / "clients_roster.json"
    path.write_text(
        json.dumps(
            {
                "clients": [
                    {
                        "client_id": "THW-VAUGHN",
                        "name": "Vaughn Heyer",
                        "email": "vheyer77@gmail.com",
                        "phone": "",
                        "sms": "",
                        "last_purchase": "2 × Tirzepatide 10 mg vials",
                        "last_purchase_date": "2026-08-14",
                        "due_for": "Reorder outreach",
                        "contact_gaps": ["phone", "sms"],
                        "status": "client",
                        "notes": "Email on file. Mobile is not.",
                    },
                    {
                        "client_id": "THW-STACY",
                        "name": "Stacy Deguerra",
                        "email": "",
                        "phone": "",
                        "sms": "",
                        "last_purchase": "KLOW / CLO protocol",
                        "due_for": "Tirzepatide weekly",
                        "contact_gaps": ["email", "phone", "sms"],
                        "status": "client",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def test_stamp_includes_inventory_lots_and_contact_gaps(tmp_path):
    _write_lots(tmp_path)
    _write_roster(tmp_path)
    payload = stamp_payload(invoice_id="THW-INV-TEST-1", reason="invoice")
    text = format_stamp(payload)
    assert payload["invoice_id"] == "THW-INV-TEST-1"
    assert payload["vials_on_hand_total"] == 50
    assert payload["gap_count"] == 2
    assert "KLOW — 50 on hand" in text
    assert "KLOW-TEST" in text
    assert "Vaughn Heyer" in text
    assert "vheyer77@gmail.com" in text
    assert "Stacy Deguerra" in text
    assert "NOT ON FILE" in text
    assert "missing phone, sms" in text
    assert "Collect mobile (text) and email" in text
    assert "THW-INV-TEST-1" in stamp_subject(invoice_id="THW-INV-TEST-1")


def test_stamp_cli_prints_body(tmp_path, capsys):
    _write_lots(tmp_path)
    _write_roster(tmp_path)
    assert main(["stamp", "--invoice-id", "THW-INV-CLI"]) == 0
    out = capsys.readouterr().out
    assert "TrueHold Wellness — inventory / lots / client stamp" in out
    assert "THW-INV-CLI" in out
    assert "Vaughn Heyer" in out


def test_stamp_email_dry_run_logs(tmp_path, capsys):
    _write_lots(tmp_path)
    _write_roster(tmp_path)
    assert main(["stamp-email", "--invoice-id", "THW-INV-DRY", "--dry-run"]) == 0
    captured = capsys.readouterr()
    assert "Vaughn Heyer" in captured.out
    assert "dry-run" in captured.err
    log = (tmp_path / "stamp_log.jsonl").read_text(encoding="utf-8")
    assert "THW-INV-DRY" in log
    assert "dry_run" in log


def test_stamp_email_sends_via_smtp(tmp_path, monkeypatch):
    _write_lots(tmp_path)
    _write_roster(tmp_path)
    monkeypatch.setenv("WELLNESS_SMTP_USERNAME", "cardanomint@gmail.com")
    monkeypatch.setenv("WELLNESS_SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("WELLNESS_STAMP_FROM", "cardanomint@gmail.com")
    monkeypatch.setenv("WELLNESS_STAMP_TO", "trueholdwellness@gmail.com")
    sent: list[EmailMessage] = []

    def fake_send(settings, message):
        sent.append(message)
        assert settings["username"] == "cardanomint@gmail.com"
        assert settings["host"] == "smtp.gmail.com"

    result = send_stamp_email(invoice_id="THW-INV-SMTP", reason="invoice", opener=fake_send)
    assert result["delivered"] is True
    assert result["status"] == "sent"
    assert sent[0]["To"] == "trueholdwellness@gmail.com"
    assert "THW-INV-SMTP" in sent[0]["Subject"]
    assert "KLOW-TEST" in sent[0].get_content()


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.sent.append({"chat_id": chat_id, "text": text})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None, parse_mode=None, message_effect_id=None):
        self.sent.append({"chat_id": chat_id, "photo": str(path), "caption": caption})
        return {"ok": True}

    def send_document(self, chat_id, path, caption="", reply_markup=None, filename=None, parse_mode=None, message_effect_id=None):
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        return {"ok": True}

    def edit_message_reply_markup(self, chat_id, message_id, reply_markup=None):
        return {"ok": True}

    def edit_message_caption(self, chat_id, message_id, caption, reply_markup=None, parse_mode=None):
        return {"ok": True}


def test_confirmed_order_writes_stamp_log(tmp_path):
    from wellness_agent.clients import save_client_phone

    _write_lots(tmp_path)
    _write_roster(tmp_path)
    save_client_phone("88", "7025550100", source="typed", user_id="88", name="Pat")
    tg = _FakeTelegram()
    result = handle_telegram_update(
        {
            "callback_query": {
                "id": "cb-stamp",
                "data": "w:yes:klow:1",
                "from": {"id": 88},
                "message": {"message_id": 9, "chat": {"id": 88, "type": "private"}},
            }
        },
        tg,
    )
    assert result["action"] == "order-confirm"
    log = (tmp_path / "stamp_log.jsonl").read_text(encoding="utf-8")
    assert "telegram-interest-order" in log
    assert "queued_no_smtp" in log
    assert "Pat" in format_stamp()
