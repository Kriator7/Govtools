#!/usr/bin/env python3
"""Refuse cloud, Funnel, reserved ports, and business-bot reuse for Nod.

House overlay: nod/house.env.example
Official stack: https://nod.n8n.io/docs/deploy/self-host/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVERLAY_PATH = ROOT / "nod" / "house.env.example"
README_PATH = ROOT / "nod" / "README.md"
SKILL_PATH = ROOT / "nod" / "SKILL.md"
UPSTREAM_PATH = ROOT / "nod" / "UPSTREAM.json"

SECRET_KEYS = frozenset(
    {"NOD_AUTH_TOKEN", "NOD_VAULT_KEY", "NOD_POSTGRES_PASSWORD", "COMPOSE_PROJECT_NAME"}
)
CHANNEL_PREFIXES = ("TELEGRAM_", "WHATSAPP_")
REQUIRED_OVERLAY = {
    "PORT": "4310",
    "NOD_BIND_ADDRESS": "127.0.0.1",
    "NOD_PUBLIC_URL": "http://localhost:4310",
    "NOD_ANALYTICS_ENABLED": "false",
    "NOD_FEEDBACK_ENABLED": "false",
    "NOD_ONBOARDING_EMAIL_URL": "",
    "NOD_FEEDBACK_URL": "",
    "NOD_TRACES_URL": "",
    "LLM_PROVIDER": "compatible",
    "OPENAI_COMPATIBLE_BASE_URL": "http://host.docker.internal:11434/v1",
    "OPENAI_COMPATIBLE_API_KEY": "",
    "LLM_MODEL": "",
}
RESERVED_PORTS = {
    80: "bundled HTTPS profile (not enabled)",
    443: "bundled HTTPS profile (not enabled)",
    5000: "never use port 5000",
    3848: "HUD",
    5432: "realtor-agent postgres",
    6379: "realtor-agent redis",
    8010: "Colibri",
    8011: "Colibri proxy",
    8080: "realtor-agent api",
    11434: "Ollama",
    15678: "house n8n",
    15679: "n8n bridge",
}
FORBIDDEN_BOTS = (
    "Mr_North_bot",
    "THWellness_bot",
    "PirateEye_bot",
    "Npeppers_bot",
)
FORBIDDEN_VALUE_FRAGMENTS = (
    "composio.n8n.cloud",
    "n8n.cloud",
    "railway.app",
    "tailscale funnel",
    "funnel.ts.net",
    "boxd.",
)
REQUIRED_DOC_PHRASES = (
    "self-hosted only",
    "not** the n8n AI Assistant",
    "SSH tunnel",
    "Tailscale Funnel",
    "@Mr_North_bot",
    "@THWellness_bot",
    "@PirateEye_bot",
    "Cursor cloud VM",
    "host.docker.internal",
)
PINNED_COMMIT = "4178ac0f7e712dd3c1e392e0161aec81af8beb64"
ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = ENV_LINE.match(line)
        if not match:
            raise ValueError(f"invalid env line: {raw!r}")
        key, value = match.group(1), match.group(2)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def load_env_file(path: Path) -> dict[str, str]:
    return parse_env_text(path.read_text(encoding="utf-8"))


def _looks_secret(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if stripped.startswith("http://") or stripped.startswith("https://"):
        return False
    return len(stripped) >= 16


def check_values(env: dict[str, str], *, overlay: bool) -> list[str]:
    errors: list[str] = []
    blob = " ".join(f"{key}={value}" for key, value in env.items())
    for bot in FORBIDDEN_BOTS:
        if bot.lower() in blob.lower():
            errors.append(f"protected Telegram bot {bot} must not appear in Nod env values")

    for key, value in env.items():
        lowered = value.lower()
        for fragment in FORBIDDEN_VALUE_FRAGMENTS:
            if fragment in lowered:
                errors.append(f"{key} contains forbidden host or product {fragment!r}")
        if overlay and key in SECRET_KEYS:
            errors.append(f"overlay must not set {key}; setup.sh owns that secret")
        if key.startswith(CHANNEL_PREFIXES) and value.strip():
            errors.append(f"{key} must stay empty so Channels stay app-managed")

    if overlay:
        for key, expected in REQUIRED_OVERLAY.items():
            if key not in env:
                errors.append(f"overlay missing {key}")
            elif env[key] != expected:
                errors.append(f"overlay {key} must be {expected!r}, got {env[key]!r}")
        extra = sorted(set(env) - set(REQUIRED_OVERLAY))
        if extra:
            errors.append("overlay has unexpected keys: " + ", ".join(extra))
        for key, value in env.items():
            if key not in SECRET_KEYS and _looks_secret(value):
                errors.append(f"overlay {key} looks like a secret; keep secrets in the live .env only")

    port_raw = env.get("PORT", "")
    try:
        port = int(port_raw)
    except ValueError:
        errors.append(f"PORT must be an integer, got {port_raw!r}")
        port = None
    if port is not None:
        if port in RESERVED_PORTS:
            errors.append(f"PORT {port} is reserved ({RESERVED_PORTS[port]})")
        if overlay and port != 4310:
            errors.append("house overlay PORT must stay 4310")

    bind = env.get("NOD_BIND_ADDRESS", "")
    if bind and bind not in {"127.0.0.1", "localhost"}:
        errors.append(f"NOD_BIND_ADDRESS must stay loopback, got {bind!r}")

    public_url = env.get("NOD_PUBLIC_URL", "")
    if public_url:
        allowed_origins = {
            "http://localhost:4310",
            "http://127.0.0.1:4310",
            "http://localhost:${PORT}",
        }
        if public_url not in allowed_origins:
            errors.append(
                "NOD_PUBLIC_URL must be a loopback HTTP origin on 4310, "
                f"got {public_url!r}"
            )
        if public_url.startswith("https://"):
            errors.append("HTTPS public origin is not enabled for the house stack")

    ollama = env.get("OPENAI_COMPATIBLE_BASE_URL", "")
    if ollama and "host.docker.internal:11434/v1" not in ollama:
        errors.append(
            "OPENAI_COMPATIBLE_BASE_URL must use host.docker.internal:11434/v1 "
            "(localhost inside Docker is the Nod container)"
        )
        if "localhost:11434" in ollama or "127.0.0.1:11434" in ollama:
            errors.append("do not point Nod Docker at localhost Ollama")

    for flag in ("NOD_ANALYTICS_ENABLED", "NOD_FEEDBACK_ENABLED"):
        if env.get(flag, "false").lower() not in {"false", "0", ""}:
            errors.append(f"{flag} must be false for the house stack")

    return errors


def check_docs() -> list[str]:
    errors: list[str] = []
    for path in (README_PATH, SKILL_PATH, OVERLAY_PATH, UPSTREAM_PATH):
        if not path.is_file():
            errors.append(f"required file missing: {path.relative_to(ROOT)}")
    if errors:
        return errors

    readme = README_PATH.read_text(encoding="utf-8")
    skill = SKILL_PATH.read_text(encoding="utf-8")
    combined = readme + "\n" + skill
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in combined:
            errors.append(f"docs missing required phrase: {phrase!r}")

    upstream = json.loads(UPSTREAM_PATH.read_text(encoding="utf-8"))
    if upstream.get("pinned_commit") != PINNED_COMMIT:
        errors.append(f"UPSTREAM.json pinned_commit must be {PINNED_COMMIT}")
    if "n8n-io/nod" not in str(upstream.get("source_repo", "")):
        errors.append("UPSTREAM.json must point at n8n-io/nod")
    if PINNED_COMMIT not in readme:
        errors.append("README must cite the pinned n8n-io/nod commit")
    return errors


def check_overlay() -> list[str]:
    env = load_env_file(OVERLAY_PATH)
    return check_values(env, overlay=True) + check_docs()


def apply_overlay(target: Path) -> list[str]:
    if not target.is_file():
        return [f"{target} does not exist; run official setup.sh first"]
    if target.is_symlink():
        return [f"{target} must be a regular file"]

    live = load_env_file(target)
    missing_secrets = [key for key in SECRET_KEYS if not live.get(key)]
    if missing_secrets:
        return [
            "live .env is missing setup.sh secrets: " + ", ".join(missing_secrets)
        ]

    overlay = load_env_file(OVERLAY_PATH)
    errors = check_values(overlay, overlay=True)
    if errors:
        return errors

    merged = dict(live)
    for key, value in overlay.items():
        merged[key] = value

    errors = check_values(merged, overlay=False)
    if errors:
        return errors

    lines = target.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    rewritten: list[str] = []
    for line in lines:
        stripped = line.strip()
        match = ENV_LINE.match(stripped) if stripped and not stripped.startswith("#") else None
        if match and match.group(1) in overlay:
            key = match.group(1)
            rewritten.append(f"{key}={overlay[key]}")
            seen.add(key)
        else:
            rewritten.append(line)
    for key, value in overlay.items():
        if key not in seen:
            rewritten.append(f"{key}={value}")
    text = "\n".join(rewritten) + "\n"
    target.write_text(text, encoding="utf-8")
    os.chmod(target, 0o600)
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="check",
        choices=("check", "apply"),
        help="check overlay (default) or merge it into a live setup.sh .env",
    )
    parser.add_argument(
        "--env",
        type=Path,
        help="live deployment/self-host/.env (apply requires this)",
    )
    args = parser.parse_args(argv)

    if args.command == "apply":
        if args.env is None:
            sys.stderr.write("apply requires --env path/to/.env\n")
            return 2
        errors = apply_overlay(args.env)
        if errors:
            sys.stderr.write("NOD HOUSE APPLY FAILED\n")
            for item in errors:
                sys.stderr.write(f"- {item}\n")
            return 1
        print(f"house overlay applied to {args.env}")
        return 0

    errors = check_overlay()
    if args.env is not None:
        errors.extend(check_values(load_env_file(args.env), overlay=False))
    if errors:
        sys.stderr.write("NOD HOUSE POLICY FAILED\n")
        for item in errors:
            sys.stderr.write(f"- {item}\n")
        return 1
    print("nod house overlay is self-hosted loopback-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
