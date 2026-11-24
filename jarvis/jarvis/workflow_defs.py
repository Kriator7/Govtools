"""n8n workflow documents. Initial automations are imported inactive."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jarvis.automations import AUTOMATIONS


def _ids(prefix: str) -> tuple[str, str]:
    return f"{prefix}-schedule", f"{prefix}-call"


def http_workflow(name: str, cron: str, tool: str, prefix: str) -> dict[str, Any]:
    schedule_id, call_id = _ids(prefix)
    return {
        "name": name,
        "settings": {
            "executionOrder": "v1",
            "timezone": "America/Los_Angeles",
            "saveDataSuccessExecution": "all",
            "saveDataErrorExecution": "all",
        },
        "nodes": [
            {
                "id": schedule_id,
                "name": "Schedule",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [260, 300],
                "parameters": {
                    "rule": {"interval": [{"field": "cronExpression", "expression": cron}]}
                },
            },
            {
                "id": call_id,
                "name": "Call JARVIS",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [560, 300],
                "parameters": {
                    "method": "POST",
                    "url": "http://host.docker.internal:8787/api/internal/run",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {
                                "name": "Authorization",
                                "value": "={{ 'Bearer ' + $env.JARVIS_GATEWAY_TOKEN }}",
                            }
                        ]
                    },
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": json.dumps({"tool": tool, "arguments": {}}),
                    "options": {"timeout": 20000},
                },
            },
        ],
        "connections": {
            "Schedule": {"main": [[{"node": "Call JARVIS", "type": "main", "index": 0}]]}
        },
    }


def harmless_ping() -> dict[str, Any]:
    return {
        "name": "JARVIS Harmless Ping",
        "settings": {
            "executionOrder": "v1",
            "timezone": "America/Los_Angeles",
            "saveDataSuccessExecution": "all",
            "saveDataErrorExecution": "all",
        },
        "nodes": [
            {
                "id": "harmless-schedule",
                "name": "Schedule",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [260, 300],
                "parameters": {
                    "rule": {"interval": [{"field": "cronExpression", "expression": "15 4 * * *"}]}
                },
            },
            {
                "id": "harmless-set",
                "name": "Ping",
                "type": "n8n-nodes-base.set",
                "typeVersion": 3.4,
                "position": [560, 300],
                "parameters": {
                    "assignments": {
                        "assignments": [
                            {"id": "ping-status", "name": "status", "value": "ok", "type": "string"},
                            {
                                "id": "ping-name",
                                "name": "workflow",
                                "value": "jarvis-harmless-ping",
                                "type": "string",
                            },
                            {
                                "id": "ping-effects",
                                "name": "side_effects",
                                "value": "none",
                                "type": "string",
                            },
                        ]
                    },
                    "options": {},
                },
            },
        ],
        "connections": {"Schedule": {"main": [[{"node": "Ping", "type": "main", "index": 0}]]}},
    }


def every_minute_ping() -> dict[str, Any]:
    document = harmless_ping()
    document["name"] = "JARVIS Harmless Ping Test"
    document["nodes"][0]["parameters"] = {
        "rule": {"interval": [{"field": "minutes", "minutesInterval": 1}]}
    }
    return document


def automation_workflows() -> list[dict[str, Any]]:
    rows = []
    for spec in AUTOMATIONS:
        prefix = spec["workflow"].replace(".json", "")
        rows.append(http_workflow(spec["name"], spec["cron"], spec["tool"], prefix))
    return rows


def write_files(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "jarvis-harmless-ping.json").write_text(
        json.dumps(harmless_ping(), indent=2) + "\n", encoding="utf-8"
    )
    for spec, document in zip(AUTOMATIONS, automation_workflows()):
        (directory / spec["workflow"]).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
