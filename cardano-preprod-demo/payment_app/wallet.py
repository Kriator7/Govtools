"""Local demo payment keys. Signing keys stay on disk and are never returned by the API."""

from __future__ import annotations

from pathlib import Path

from payment_app import PREPROD_MAGIC
from payment_app.node import NodeClient, NodeError, default_root


def keys_dir(root: Path | None = None) -> Path:
    path = (root or default_root()) / "keys"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_demo_wallet(client: NodeClient, root: Path | None = None) -> dict[str, str]:
    directory = keys_dir(root)
    vkey = directory / "payment.vkey"
    skey = directory / "payment.skey"
    addr = directory / "payment.addr"
    if not vkey.exists() or not skey.exists():
        client.run_checked(
            [
                "address",
                "key-gen",
                "--verification-key-file",
                str(vkey),
                "--signing-key-file",
                str(skey),
            ]
        )
    if not addr.exists() or not addr.read_text(encoding="utf-8").strip():
        client.run_checked(
            [
                "address",
                "build",
                "--payment-verification-key-file",
                str(vkey),
                "--testnet-magic",
                str(PREPROD_MAGIC),
                "--out-file",
                str(addr),
            ]
        )
    address = addr.read_text(encoding="utf-8").strip()
    if not address:
        raise NodeError("payment.addr is empty")
    if not address.startswith("addr_test"):
        raise NodeError("demo wallet is not a Preprod test address")
    return {
        "address": address,
        "verificationKeyFile": str(vkey),
        "signingKeyFile": str(skey),
        "addressFile": str(addr),
    }
