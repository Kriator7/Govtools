"""HTTP helpers. Webpage reads refuse non-public addresses."""

from __future__ import annotations

import ipaddress
import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class HttpError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def assert_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HttpError("only public http and https URLs are allowed")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
        raise HttpError("refusing a local or metadata host")
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise HttpError(f"could not resolve host: {exc}") from exc
    if not infos:
        raise HttpError("host did not resolve")
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise HttpError("refusing a non-public address")


def request_json(
    method: str,
    url: str,
    payload: Any = None,
    headers: dict[str, str] | None = None,
    timeout: float = 8,
    *,
    public_only: bool = False,
) -> tuple[int, Any]:
    if public_only:
        assert_public_url(url)
    data = None
    req_headers = {"Accept": "application/json", "User-Agent": "jarvis-mark-vii"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = Request(url, data=data, headers=req_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(1_000_000)
            status = response.status
    except HTTPError as exc:
        raw = exc.read(200_000)
        status = exc.code
    except URLError as exc:
        raise HttpError(f"request failed: {exc.reason}") from exc
    text = raw.decode("utf-8", errors="replace")
    if not text:
        return status, None
    try:
        return status, json.loads(text)
    except json.JSONDecodeError:
        return status, text


def read_text(url: str, timeout: float = 8, limit: int = 100_000) -> str:
    assert_public_url(url)
    request = Request(url, headers={"User-Agent": "jarvis-mark-vii"}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(limit + 1)
            final = response.geturl()
    except HTTPError as exc:
        raise HttpError(f"page returned HTTP {exc.code}", exc.code) from exc
    except URLError as exc:
        raise HttpError(f"request failed: {exc.reason}") from exc
    assert_public_url(final)
    if len(raw) > limit:
        raw = raw[:limit]
    return raw.decode("utf-8", errors="replace")
