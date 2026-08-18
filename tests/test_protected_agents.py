"""Protected business agents cannot be deleted without two confirmations."""

import json
from pathlib import Path

from scripts.check_protected_agents import (
    CONFIRMATION_PATH,
    confirmation_allows,
    inspect_agent,
    load_manifest,
    main,
    phrase_for,
)

ROOT = Path(__file__).resolve().parent.parent


def test_all_protected_agents_are_present():
    assert main() == 0


def test_manifest_lists_the_three_business_agents():
    ids = [agent["id"] for agent in load_manifest()["agents"]]
    assert ids == ["mr-north", "realtor-agent", "truehold-wellness"]
    for agent in load_manifest()["agents"]:
        assert not inspect_agent(agent)


def test_confirmation_phrases_are_exact():
    assert (
        phrase_for("truehold-wellness", "1")
        == "I CONFIRM DELETE OF truehold-wellness FROM BUSINESS INFRASTRUCTURE"
    )
    assert (
        phrase_for("truehold-wellness", "2")
        == "I INDEPENDENTLY CONFIRM DELETE OF truehold-wellness FROM BUSINESS INFRASTRUCTURE"
    )


def test_live_confirmation_file_is_not_committed():
    assert not CONFIRMATION_PATH.exists(), (
        "Do not commit .github/DELETE_AGENT_CONFIRMATION.json unless you are intentionally "
        "deleting a protected agent with two human confirmations."
    )


def test_incomplete_confirmation_is_rejected():
    errors = confirmation_allows("truehold-wellness", {"agent_id": "truehold-wellness", "reason": "x"})
    assert errors
    assert any("confirmer" in item or "reason" in item or "warning" in item for item in errors)


def test_example_confirmation_is_not_a_valid_override():
    example = json.loads(
        (ROOT / ".github" / "DELETE_AGENT_CONFIRMATION.example.json").read_text(encoding="utf-8")
    )
    assert "REPLACE_WITH" in example["agent_id"]
    assert "<agent_id>" in example["confirmer_1"]["phrase"]
    assert "INDEPENDENTLY CONFIRM" in example["confirmer_2"]["phrase"]
