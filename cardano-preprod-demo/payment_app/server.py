"""HTTP GUI for Preprod node status and gated sending."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from payment_app.node import NodeClient, NodeError, NodeNotReady, default_root, status_payload
from payment_app.send import send_ada, send_error_payload
from payment_app.wallet import ensure_demo_wallet, utxo_lovelace

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _json_bytes(payload: dict[str, Any], status: int = 200) -> tuple[int, bytes]:
    body = json.dumps(payload, indent=2).encode("utf-8")
    return status, body


class PaymentHandler(BaseHTTPRequestHandler):
    server_version = "preprod-payment/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        code, body = _json_bytes(payload, status)
        self._send(code, body, "application/json; charset=utf-8")

    def _client(self) -> NodeClient:
        return NodeClient.from_env(default_root())

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            html = (STATIC_DIR / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/health":
            self._send_json({"ok": True, "network": "preprod", "networkMagic": 1})
            return
        if path == "/api/status":
            self._send_json(status_payload())
            return
        if path == "/api/wallet":
            try:
                client = self._client()
                wallet = ensure_demo_wallet(client)
                utxo_error = None
                utxos: dict[str, Any] = {}
                try:
                    utxos = client.query_utxo(wallet["address"])
                except (NodeError, OSError) as exc:
                    utxo_error = str(exc)
                lovelace = utxo_lovelace(utxos)
                self._send_json(
                    {
                        "address": wallet["address"],
                        "stakeAddress": wallet.get("stakeAddress") or None,
                        "utxos": utxos,
                        "lovelace": lovelace,
                        "ada": lovelace / 1_000_000,
                        "funded": lovelace > 0,
                        "utxoError": utxo_error,
                        "blockfrost": False,
                    }
                )
            except (NodeError, OSError) as exc:
                self._send_json({"error": str(exc), "blockfrost": False}, status=503)
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/send":
            self._send_json({"error": "not found"}, status=404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "invalid JSON"}, status=400)
            return
        client = self._client()
        tip = None
        try:
            tip = client.query_tip()
            result = send_ada(
                client,
                destination=str(body.get("destination") or ""),
                ada_amount=body.get("amount") or 0,
                tip=tip,
            )
            self._send_json(result)
        except NodeNotReady as exc:
            self._send_json(send_error_payload(exc, tip), status=409)
        except (NodeError, OSError, ValueError) as exc:
            self._send_json(send_error_payload(exc, tip), status=400)


def serve(host: str = "0.0.0.0", port: int = 8787) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), PaymentHandler)
    print(f"Preprod payment GUI on http://{host}:{port} (node socket only, magic 1)", flush=True)
    httpd.serve_forever()
    return httpd
