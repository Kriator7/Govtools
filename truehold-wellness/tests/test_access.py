from wellness_agent.access import (
    STAFF_DENIED,
    env_staff_user_ids,
    is_operator,
    staff_notify_chat_ids,
)


def test_empty_allowlist_is_fail_closed():
    assert env_staff_user_ids() == set()
    assert is_operator("99", "99", "private") is False


def test_env_user_id_grants_only_matching_private_chat(monkeypatch):
    monkeypatch.setenv("WELLNESS_OPERATOR_USER_IDS", "42, 99")
    assert env_staff_user_ids() == {"42", "99"}
    assert is_operator("42", "42", "private") is True
    assert is_operator("99", "99", "private") is True
    assert is_operator("7", "7", "private") is False


def test_group_chat_never_grants_even_if_user_allowlisted(monkeypatch):
    monkeypatch.setenv("WELLNESS_OPERATOR_USER_IDS", "42")
    assert is_operator("42", "-100", "supergroup") is False
    assert is_operator("42", "42", "group") is False


def test_missing_from_id_never_grants(monkeypatch):
    monkeypatch.setenv("WELLNESS_OPERATOR_USER_IDS", "42")
    assert is_operator("", "42", "private") is False
    assert is_operator(None, "42", "private") is False


def test_user_chat_mismatch_never_grants(monkeypatch):
    monkeypatch.setenv("WELLNESS_OPERATOR_USER_IDS", "42")
    assert is_operator("42", "99", "private") is False


def test_group_ids_in_env_are_ignored(monkeypatch):
    monkeypatch.setenv("WELLNESS_TELEGRAM_CHAT_ID", "-100123")
    monkeypatch.setenv("WELLNESS_OPERATOR_USER_IDS", "")
    assert env_staff_user_ids() == set()
    assert staff_notify_chat_ids() == []
    assert is_operator("555", "-100123", "supergroup") is False


def test_operator_json_cannot_grant_staff(tmp_path, monkeypatch):
    path = tmp_path / "operator.json"
    path.write_text('{"chat_ids": ["501"], "user_ids": ["501"]}', encoding="utf-8")
    monkeypatch.setenv("WELLNESS_OPERATOR_PATH", str(path))
    monkeypatch.setenv("WELLNESS_OPERATOR_USER_IDS", "")
    assert is_operator("501", "501", "private") is False
    assert staff_notify_chat_ids() == []
    from wellness_agent.operator_store import load_operator_user_ids

    assert "501" in load_operator_user_ids()


def test_staff_denied_copy_does_not_name_commands():
    assert "/inbox" not in STAFF_DENIED
    assert "/staff" not in STAFF_DENIED
