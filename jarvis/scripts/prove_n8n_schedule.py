"""Import workflows and prove one harmless n8n schedule execution.

The script writes execution metadata only. It does not print credentials.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from jarvis.automations import AUTOMATIONS
from jarvis.credentials import CredentialStore
from jarvis.n8n_client import N8nClient, N8nError
from jarvis.workflow_defs import automation_workflows, every_minute_ping, harmless_ping

EVIDENCE = Path("/opt/cursor/artifacts/n8n-harmless-ping.json")
LAB = "http://127.0.0.1:15680"


def main() -> int:
    creds = CredentialStore.load()
    email = creds.get("N8N_OWNER_EMAIL") or "jarvis-lab@example.com"
    password = creds.get("N8N_OWNER_PASSWORD")
    if not password:
        print("N8N_OWNER_PASSWORD missing", file=sys.stderr)
        return 2
    client = N8nClient(LAB)
    if not client.health():
        print("n8n healthz failed", file=sys.stderr)
        return 1
    cookie = _session(client, email, password)
    api_key = creds.get("N8N_API_KEY")
    if not api_key:
        api_key = client.create_api_key(cookie)
        creds.write_key("N8N_API_KEY", api_key)
    test = client.create_workflow(api_key, every_minute_ping())
    test_id = test["id"]
    client.set_active(api_key, test_id, True)
    execution = _wait_for_success(client, api_key, test_id)
    client.set_active(api_key, test_id, False)
    client.delete_workflow(api_key, test_id)
    imported = []
    for document in [harmless_ping(), *automation_workflows()]:
        created = client.create_workflow(api_key, document)
        active = bool(created.get("active"))
        imported.append({"name": document["name"], "id": created["id"], "active": active})
        if active:
            client.set_active(api_key, created["id"], False)
            active = False
            imported[-1]["active"] = False
    evidence = {
        "n8n": LAB,
        "image": "n8nio/n8n:2.3.2",
        "house_n8n": "http://127.0.0.1:15678",
        "harmless_execution": execution,
        "test_workflow_deleted": True,
        "imported_inactive": imported,
        "initial_automation_count": len(AUTOMATIONS),
        "all_initial_inactive": all(item["active"] is False for item in imported if item["name"] != "JARVIS Harmless Ping"),
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(EVIDENCE), "execution_status": execution.get("status"), "inactive": evidence["all_initial_inactive"]}))
    if execution.get("status") != "success":
        return 1
    if not evidence["all_initial_inactive"]:
        return 1
    return 0


def _session(client: N8nClient, email: str, password: str) -> str:
    try:
        return client.login(email, password)
    except N8nError:
        return client.setup_owner(email, password)


def _wait_for_success(client: N8nClient, api_key: str, workflow_id: str) -> dict:
    deadline = time.time() + 100
    last: dict = {"status": "waiting"}
    while time.time() < deadline:
        rows = client.list_executions(api_key, workflow_id)
        for row in rows:
            if row.get("status") == "success":
                return {
                    "id": row.get("id"),
                    "status": "success",
                    "startedAt": row.get("startedAt"),
                    "stoppedAt": row.get("stoppedAt"),
                    "mode": row.get("mode"),
                }
            last = {"id": row.get("id"), "status": row.get("status"), "mode": row.get("mode")}
        time.sleep(3)
    return last


if __name__ == "__main__":
    raise SystemExit(main())
