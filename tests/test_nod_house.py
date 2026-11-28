"""Nod house overlay stays self-hosted, loopback-only, and off the business bots."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_nod_house import (
    FORBIDDEN_BOTS,
    PINNED_COMMIT,
    RESERVED_PORTS,
    SECRET_KEYS,
    apply_overlay,
    check_overlay,
    check_values,
    load_env_file,
    main,
    parse_env_text,
)

ROOT = Path(__file__).resolve().parent.parent
PROTECTED = json.loads((ROOT / "protected-agents.json").read_text(encoding="utf-8"))


def _base_live_env() -> str:
    return "\n".join(
        [
            "COMPOSE_PROJECT_NAME=nod-house-test",
            "NOD_AUTH_TOKEN=test-token-not-a-real-secret",
            "NOD_VAULT_KEY=test-vault-not-a-real-secret",
            "NOD_POSTGRES_PASSWORD=test-db-not-a-real-secret",
            "PORT=4310",
            "NOD_BIND_ADDRESS=127.0.0.1",
            "NOD_PUBLIC_URL=http://localhost:4310",
            "",
        ]
    )


def test_overlay_and_docs_pass_the_house_gate():
    assert check_overlay() == []
    assert main([]) == 0


def test_overlay_is_loopback_ollama_and_analytics_off():
    env = load_env_file(ROOT / "nod" / "house.env.example")
    assert env["NOD_BIND_ADDRESS"] == "127.0.0.1"
    assert env["PORT"] == "4310"
    assert env["NOD_PUBLIC_URL"] == "http://localhost:4310"
    assert env["OPENAI_COMPATIBLE_BASE_URL"] == "http://host.docker.internal:11434/v1"
    assert env["NOD_ANALYTICS_ENABLED"] == "false"
    assert env["NOD_FEEDBACK_ENABLED"] == "false"
    assert env["LLM_PROVIDER"] == "compatible"
    for key in SECRET_KEYS:
        assert key not in env
    for bot in FORBIDDEN_BOTS:
        assert bot not in Path(ROOT / "nod" / "house.env.example").read_text(encoding="utf-8")


def test_nod_is_not_a_protected_business_agent():
    ids = [agent["id"] for agent in PROTECTED["agents"]]
    assert ids == ["mr-north", "realtor-agent", "truehold-wellness"]
    assert "nod" not in ids


def test_pinned_commit_matches_upstream_manifest():
    upstream = json.loads((ROOT / "nod" / "UPSTREAM.json").read_text(encoding="utf-8"))
    assert upstream["pinned_commit"] == PINNED_COMMIT
    assert upstream["source_repo"] == "https://github.com/n8n-io/nod"


def test_reserved_n8n_port_is_rejected():
    env = load_env_file(ROOT / "nod" / "house.env.example")
    env["PORT"] = "15678"
    errors = check_values(env, overlay=False)
    assert any("15678" in item and "n8n" in item for item in errors)


@pytest.mark.parametrize("port", sorted(RESERVED_PORTS))
def test_every_reserved_house_port_is_rejected(port: int):
    env = load_env_file(ROOT / "nod" / "house.env.example")
    env["PORT"] = str(port)
    errors = check_values(env, overlay=False)
    assert any(str(port) in item for item in errors)


def test_public_https_origin_is_rejected():
    env = load_env_file(ROOT / "nod" / "house.env.example")
    env["NOD_PUBLIC_URL"] = "https://nod.example.com"
    errors = check_values(env, overlay=False)
    assert any("loopback" in item or "HTTPS" in item for item in errors)


def test_composio_cloud_proxy_is_rejected():
    env = load_env_file(ROOT / "nod" / "house.env.example")
    env["NOD_COMPOSIO_PROXY_URL"] = "https://composio.n8n.cloud"
    errors = check_values(env, overlay=False)
    assert any("composio.n8n.cloud" in item for item in errors)


def test_localhost_ollama_from_docker_is_rejected():
    env = load_env_file(ROOT / "nod" / "house.env.example")
    env["OPENAI_COMPATIBLE_BASE_URL"] = "http://localhost:11434/v1"
    errors = check_values(env, overlay=False)
    assert any("host.docker.internal" in item for item in errors)
    assert any("localhost Ollama" in item for item in errors)


@pytest.mark.parametrize("bot", FORBIDDEN_BOTS)
def test_protected_bot_names_are_rejected(bot: str):
    env = load_env_file(ROOT / "nod" / "house.env.example")
    env["TELEGRAM_BOT_TOKEN"] = f"x-{bot}-x"
    errors = check_values(env, overlay=False)
    assert any(bot in item for item in errors)
    assert any("TELEGRAM_BOT_TOKEN" in item for item in errors)


def test_apply_merges_overlay_and_keeps_setup_secrets(tmp_path: Path):
    target = tmp_path / ".env"
    target.write_text(_base_live_env(), encoding="utf-8")
    assert apply_overlay(target) == []
    merged = load_env_file(target)
    assert merged["COMPOSE_PROJECT_NAME"] == "nod-house-test"
    assert merged["NOD_AUTH_TOKEN"] == "test-token-not-a-real-secret"
    assert merged["NOD_VAULT_KEY"] == "test-vault-not-a-real-secret"
    assert merged["NOD_POSTGRES_PASSWORD"] == "test-db-not-a-real-secret"
    assert merged["NOD_BIND_ADDRESS"] == "127.0.0.1"
    assert merged["OPENAI_COMPATIBLE_BASE_URL"] == "http://host.docker.internal:11434/v1"
    assert merged["NOD_ANALYTICS_ENABLED"] == "false"
    assert oct(target.stat().st_mode & 0o777) == "0o600"


def test_apply_refuses_to_invent_a_live_env(tmp_path: Path):
    missing = tmp_path / "missing.env"
    errors = apply_overlay(missing)
    assert errors
    assert any("setup.sh" in item for item in errors)


def test_apply_refuses_an_env_without_vault_key(tmp_path: Path):
    target = tmp_path / ".env"
    target.write_text("COMPOSE_PROJECT_NAME=x\nNOD_AUTH_TOKEN=x\nNOD_POSTGRES_PASSWORD=x\n")
    errors = apply_overlay(target)
    assert any("NOD_VAULT_KEY" in item for item in errors)


def test_parse_env_ignores_comments():
    env = parse_env_text("# TELEGRAM_BOT_TOKEN=do-not-use\nPORT=4310\n")
    assert env == {"PORT": "4310"}


def test_root_readme_lists_nod_without_promoting_it_to_business_infra():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Nod" in text
    assert "self-hosted only" in text
    assert "@Mr_North_bot" in text
    assert "nod/" in text
