"""n8n public API and owner bootstrap. Secrets are not included in error text."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class N8nError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _request(
    method: str,
    url: str,
    payload: Any = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15,
) -> tuple[int, dict[str, str], Any]:
    data = None
    req_headers = {"Accept": "application/json", "User-Agent": "jarvis-mark-vii"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=req_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(1_000_000)
            status = response.status
            header_map = {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as exc:
        raw = exc.read(200_000)
        status = exc.code
        header_map = {key.lower(): value for key, value in exc.headers.items()} if exc.headers else {}
    except URLError as exc:
        raise N8nError(f"n8n request failed: {exc.reason}") from exc
    text = raw.decode("utf-8", errors="replace")
    if not text:
        body: Any = None
    else:
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            body = text[:300]
    return status, header_map, body


class N8nClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")

    def health(self) -> bool:
        status, _headers, _body = _request("GET", f"{self.base}/healthz", timeout=3)
        return status == 200

    def setup_owner(self, email: str, password: str) -> str:
        status, headers, body = _request(
            "POST",
            f"{self.base}/rest/owner/setup",
            {"email": email, "firstName": "Jarvis", "lastName": "Lab", "password": password},
        )
        if status not in {200, 201}:
            raise N8nError(f"owner setup returned HTTP {status}", status)
        return _cookie(headers, body)

    def login(self, email: str, password: str) -> str:
        status, headers, body = _request(
            "POST",
            f"{self.base}/rest/login",
            {"emailOrLdapLoginId": email, "password": password},
        )
        if status != 200:
            raise N8nError(f"login returned HTTP {status}", status)
        return _cookie(headers, body)

    def create_api_key(self, cookie: str, label: str = "jarvis-gateway") -> str:
        status, _headers, listed = _request(
            "GET",
            f"{self.base}/rest/api-keys/scopes",
            headers={"Cookie": cookie},
        )
        if status != 200:
            raise N8nError(f"scope list returned HTTP {status}", status)
        available = listed.get("data") if isinstance(listed, dict) else listed
        if not isinstance(available, list):
            raise N8nError("scope list was empty", status)
        needed = [
            "workflow:create",
            "workflow:read",
            "workflow:list",
            "workflow:update",
            "workflow:activate",
            "workflow:deactivate",
            "workflow:delete",
            "execution:list",
            "execution:read",
        ]
        scopes = [item for item in needed if item in available]
        if len(scopes) != len(needed):
            raise N8nError("n8n did not offer the workflow scopes JARVIS needs", status)
        import time

        status, _headers, body = _request(
            "POST",
            f"{self.base}/rest/api-keys",
            {"label": label, "expiresAt": int((time.time() + 86400 * 365) * 1000), "scopes": scopes},
            headers={"Cookie": cookie},
        )
        if status not in {200, 201} or not isinstance(body, dict):
            raise N8nError(f"API key create returned HTTP {status}", status)
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        raw = data.get("rawApiKey") if isinstance(data, dict) else None
        if not isinstance(raw, str) or len(raw) < 20:
            raise N8nError("API key response did not include a raw key", status)
        return raw

    def create_workflow(self, api_key: str, document: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "name": document["name"],
            "nodes": document["nodes"],
            "connections": document["connections"],
            "settings": document["settings"],
        }
        status, _headers, body = _request(
            "POST",
            f"{self.base}/api/v1/workflows",
            payload,
            headers={"X-N8N-API-KEY": api_key},
        )
        if status not in {200, 201} or not isinstance(body, dict) or not body.get("id"):
            fallback = {"executionOrder": "v1", "timezone": "America/Los_Angeles"}
            payload["settings"] = fallback
            status, _headers, body = _request(
                "POST",
                f"{self.base}/api/v1/workflows",
                payload,
                headers={"X-N8N-API-KEY": api_key},
            )
        if status not in {200, 201} or not isinstance(body, dict) or not body.get("id"):
            raise N8nError(f"workflow create returned HTTP {status}", status)
        return body

    def set_active(self, api_key: str, workflow_id: str, active: bool) -> None:
        action = "activate" if active else "deactivate"
        status, _headers, _body = _request(
            "POST",
            f"{self.base}/api/v1/workflows/{workflow_id}/{action}",
            headers={"X-N8N-API-KEY": api_key},
        )
        if status not in {200, 201}:
            raise N8nError(f"{action} returned HTTP {status}", status)

    def get_workflow(self, api_key: str, workflow_id: str) -> dict[str, Any]:
        status, _headers, body = _request(
            "GET",
            f"{self.base}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": api_key},
        )
        if status != 200 or not isinstance(body, dict):
            raise N8nError(f"workflow read returned HTTP {status}", status)
        return body

    def list_executions(self, api_key: str, workflow_id: str) -> list[dict[str, Any]]:
        status, _headers, body = _request(
            "GET",
            f"{self.base}/api/v1/executions?workflowId={workflow_id}&limit=10",
            headers={"X-N8N-API-KEY": api_key},
        )
        if status != 200 or not isinstance(body, dict):
            raise N8nError(f"executions returned HTTP {status}", status)
        data = body.get("data")
        return data if isinstance(data, list) else []

    def delete_workflow(self, api_key: str, workflow_id: str) -> None:
        status, _headers, _body = _request(
            "DELETE",
            f"{self.base}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": api_key},
        )
        if status not in {200, 204}:
            raise N8nError(f"delete returned HTTP {status}", status)


def _cookie(headers: dict[str, str], body: Any) -> str:
    raw = headers.get("set-cookie", "")
    if "n8n-auth=" in raw:
        part = raw.split("n8n-auth=", 1)[1]
        return "n8n-auth=" + part.split(";", 1)[0]
    if isinstance(body, dict):
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        token = data.get("token") if isinstance(data, dict) else None
        if isinstance(token, str) and token:
            return f"n8n-auth={token}"
    raise N8nError("n8n did not return an auth cookie")
