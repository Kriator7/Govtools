#!/usr/bin/env python3
"""Fail CI if the three Telegram agents share code, tokens, or Docker context.

Each agent is a separate Docker build context. They must not import each other
or read another agent's bot token.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AGENTS = (
    {
        "id": "mr-north",
        "root": ROOT / "mr_north",
        "source_dirs": (ROOT / "mr_north",),
        "skip_dir_names": frozenset({"tests", "data", "scripts"}),
        "forbidden_modules": frozenset({"wellness_agent", "thw", "app"}),
        "forbidden_token_envs": frozenset({"TELEGRAM_BOT_TOKEN"}),
        "required_token_env": "NORTH_TELEGRAM_BOT_TOKEN",
        "dockerfile": ROOT / "mr_north" / "Dockerfile",
        "forbidden_copy_tokens": ("truehold-wellness", "realtor-agent", "THWellness", "PirateEye"),
    },
    {
        "id": "truehold-wellness",
        "root": ROOT / "truehold-wellness",
        "source_dirs": (ROOT / "truehold-wellness" / "wellness_agent", ROOT / "truehold-wellness" / "thw"),
        "skip_dir_names": frozenset(),
        "forbidden_modules": frozenset({"mr_north", "app"}),
        "forbidden_token_envs": frozenset({"NORTH_TELEGRAM_BOT_TOKEN"}),
        "required_token_env": "TELEGRAM_BOT_TOKEN",
        "dockerfile": ROOT / "truehold-wellness" / "Dockerfile",
        "forbidden_copy_tokens": ("mr_north", "realtor-agent", "Mr_North", "PirateEye"),
    },
    {
        "id": "realtor-agent",
        "root": ROOT / "realtor-agent",
        "source_dirs": (ROOT / "realtor-agent" / "app",),
        "skip_dir_names": frozenset(),
        "forbidden_modules": frozenset({"mr_north", "wellness_agent", "thw"}),
        "forbidden_token_envs": frozenset({"NORTH_TELEGRAM_BOT_TOKEN"}),
        "required_token_env": "TELEGRAM_BOT_TOKEN",
        "dockerfile": ROOT / "realtor-agent" / "Dockerfile",
        "forbidden_copy_tokens": ("mr_north", "truehold-wellness", "Mr_North", "THWellness"),
    },
)


def iter_python_files(source_dirs: tuple[Path, ...], skip_dir_names: frozenset[str]):
    for directory in source_dirs:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.py"):
            if any(part in skip_dir_names for part in path.relative_to(directory).parts):
                continue
            if path.name in {"pyproject.toml"}:
                continue
            yield path


def imported_modules(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


def environ_gets(tree: ast.AST) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "get":
            value = func.value
            if isinstance(value, ast.Attribute) and value.attr == "environ":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    keys.add(node.args[0].value)
    return keys


def inspect_agent(agent: dict) -> list[str]:
    errors: list[str] = []
    dockerfile: Path = agent["dockerfile"]
    if not dockerfile.is_file():
        errors.append(f"{agent['id']}: Dockerfile is missing at {dockerfile.relative_to(ROOT)}")
    else:
        text = dockerfile.read_text(encoding="utf-8")
        for token in agent["forbidden_copy_tokens"]:
            if token in text:
                errors.append(
                    f"{agent['id']}: Dockerfile must not reference {token!r} "
                    f"({dockerfile.relative_to(ROOT)})"
                )
        compose = agent["root"] / "docker-compose.yml"
        if not compose.is_file():
            errors.append(f"{agent['id']}: docker-compose.yml is missing")
        else:
            compose_text = compose.read_text(encoding="utf-8")
            for other in ("mr_north/", "truehold-wellness/", "realtor-agent/"):
                if agent["root"].name + "/" == other:
                    continue
                if other in compose_text:
                    errors.append(f"{agent['id']}: docker-compose.yml must not reference {other}")

    for path in iter_python_files(agent["source_dirs"], agent["skip_dir_names"]):
        if path.name in {"pyproject.toml"}:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{agent['id']}: cannot parse {path.relative_to(ROOT)}: {exc}")
            continue
        imported = imported_modules(tree)
        overlap = imported.intersection(agent["forbidden_modules"])
        if overlap:
            errors.append(
                f"{agent['id']}: {path.relative_to(ROOT)} imports {sorted(overlap)}"
            )
        env_keys = environ_gets(tree)
        leak = env_keys.intersection(agent["forbidden_token_envs"])
        if leak:
            errors.append(
                f"{agent['id']}: {path.relative_to(ROOT)} reads foreign token env {sorted(leak)}"
            )
    return errors


def main() -> int:
    errors: list[str] = []
    for agent in AGENTS:
        errors.extend(inspect_agent(agent))
    if errors:
        sys.stderr.write("Agent isolation failed:\n")
        for item in errors:
            sys.stderr.write(f"  - {item}\n")
        return 1
    sys.stdout.write("ok: three Telegram agents are isolated\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
