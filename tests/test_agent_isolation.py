"""The three Telegram agents must not share code, tokens, or Docker context."""

from pathlib import Path

from scripts.check_agent_isolation import AGENTS, inspect_agent, main

ROOT = Path(__file__).resolve().parent.parent


def test_isolation_script_passes():
    assert main() == 0


def test_each_agent_has_its_own_docker_files():
    for agent in AGENTS:
        folder = agent["root"]
        assert (folder / "Dockerfile").is_file(), agent["id"]
        assert (folder / "docker-compose.yml").is_file(), agent["id"]
        assert (folder / ".env.example").is_file(), agent["id"]
        assert inspect_agent(agent) == [], agent["id"]


def test_root_readme_does_not_contain_product_manuals():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Strait of Hormuz" not in text
    assert "/order" not in text
    assert "MLS/API" not in text
    for folder in ("mr_north/", "truehold-wellness/", "realtor-agent/"):
        assert folder in text
