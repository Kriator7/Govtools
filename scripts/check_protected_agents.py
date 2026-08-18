#!/usr/bin/env python3
"""Fail CI if a protected business agent is missing without two confirmations.

Protected list: protected-agents.json
Deletion override: .github/DELETE_AGENT_CONFIRMATION.json (must not be the example file)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "protected-agents.json"
CONFIRMATION_PATH = ROOT / ".github" / "DELETE_AGENT_CONFIRMATION.json"
REQUIRED_WARNING = "THIS DELETES PRODUCTION BUSINESS INFRASTRUCTURE"


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        raise SystemExit(f"protected-agents.json is missing at {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def phrase_for(agent_id: str, kind: str) -> str:
    if kind == "1":
        return f"I CONFIRM DELETE OF {agent_id} FROM BUSINESS INFRASTRUCTURE"
    return f"I INDEPENDENTLY CONFIRM DELETE OF {agent_id} FROM BUSINESS INFRASTRUCTURE"


def load_confirmation() -> dict | None:
    if not CONFIRMATION_PATH.is_file():
        return None
    payload = json.loads(CONFIRMATION_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("DELETE_AGENT_CONFIRMATION.json must be a JSON object")
    return payload


def confirmation_allows(agent_id: str, payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("agent_id") != agent_id:
        errors.append(
            f"confirmation agent_id {payload.get('agent_id')!r} does not match missing agent {agent_id!r}"
        )
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 20 or reason.startswith("Replace this"):
        errors.append("confirmation reason must be a real business explanation (20+ characters)")
    one = payload.get("confirmer_1") or {}
    two = payload.get("confirmer_2") or {}
    name1 = str(one.get("name") or "").strip()
    name2 = str(two.get("name") or "").strip()
    if len(name1) < 3 or len(name2) < 3:
        errors.append("both confirmer_1.name and confirmer_2.name are required")
    if name1 and name2 and name1.lower() == name2.lower():
        errors.append("confirmer_1 and confirmer_2 must be two different people")
    if str(one.get("phrase") or "").strip() != phrase_for(agent_id, "1"):
        errors.append(f"confirmer_1.phrase must be exactly: {phrase_for(agent_id, '1')}")
    if str(two.get("phrase") or "").strip() != phrase_for(agent_id, "2"):
        errors.append(f"confirmer_2.phrase must be exactly: {phrase_for(agent_id, '2')}")
    if str(payload.get("warning") or "").strip() != REQUIRED_WARNING:
        errors.append(f"warning must be exactly: {REQUIRED_WARNING}")
    return errors


def inspect_agent(agent: dict) -> list[str]:
    missing: list[str] = []
    path = ROOT / agent["path"]
    if not path.is_dir():
        missing.append(f"directory {agent['path']}/ is gone")
        return missing
    for rel in agent.get("required_files") or []:
        if not (ROOT / rel).is_file():
            missing.append(f"required file {rel} is gone")
    return missing


def main() -> int:
    manifest = load_manifest()
    confirmation = load_confirmation()
    blocked: list[str] = []
    allowed_missing: set[str] = set()

    for agent in manifest["agents"]:
        problems = inspect_agent(agent)
        if not problems:
            continue
        agent_id = agent["id"]
        if confirmation is None:
            blocked.append(
                f"{agent['name']} ({agent_id}) is protected business infrastructure and is damaged or deleted: "
                + "; ".join(problems)
                + ". To remove it, two people must fill .github/DELETE_AGENT_CONFIRMATION.json "
                + "(see .github/DELETE_AGENT_CONFIRMATION.example.json)."
            )
            continue
        errors = confirmation_allows(agent_id, confirmation)
        if errors:
            blocked.append(
                f"{agent['name']} ({agent_id}) is missing ({'; '.join(problems)}) "
                f"but confirmation is invalid: {'; '.join(errors)}"
            )
            continue
        allowed_missing.add(agent_id)

    if confirmation is not None and not allowed_missing:
        blocked.append(
            ".github/DELETE_AGENT_CONFIRMATION.json is present but no matching protected agent is missing. "
            "Remove the confirmation file; do not leave a deletion override in the tree."
        )

    if blocked:
        sys.stderr.write("PROTECTED AGENT GATE FAILED\n")
        for item in blocked:
            sys.stderr.write(f"- {item}\n")
        return 1
    print("protected agents present")
    if allowed_missing:
        print("deletion confirmation accepted for: " + ", ".join(sorted(allowed_missing)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
