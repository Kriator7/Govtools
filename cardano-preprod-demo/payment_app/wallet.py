"""Local demo payment keys. Signing keys stay on disk and are never returned by the API.

Wallet shape follows Cardano testnet docs: payment key + stake key + base address.
Sources:
  https://docs.cardano.org/cardano-testnets/getting-started
  https://developers.cardano.org/docs/operate-a-stake-pool/block-producer/generating-wallet-keys/
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from payment_app import PREPROD_MAGIC
from payment_app.node import NodeClient, NodeError, default_root


def keys_dir(root: Path | None = None) -> Path:
    path = (root or default_root()) / "keys"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _is_enterprise_test_address(address: str) -> bool:
    # CIP-19 testnet enterprise (payment-only) bech32 prefix.
    return address.startswith("addr_test1v")


WALLET_LETTER_NAME = "wallet-letter.txt"


def wallet_letter_path(root: Path | None = None) -> Path:
    return keys_dir(root) / WALLET_LETTER_NAME


def write_wallet_letter(directory: Path) -> Path:
    """Write a local wallet letter with addresses and key-file contents.

    The letter stays in keys/wallet-letter.txt (mode 0600, gitignored).
    Signing keys are never returned over the HTTP API.
    """
    directory.mkdir(parents=True, exist_ok=True)
    names = (
        "payment.addr",
        "stake.addr",
        "payment.vkey",
        "stake.vkey",
        "payment.skey",
        "stake.skey",
    )
    lines = [
        "Cardano Preprod wallet letter",
        "network=preprod",
        "networkMagic=1",
        "sources=https://docs.cardano.org/cardano-testnets/getting-started",
        f"directory={directory.resolve()}",
        "",
        "This file is the wallet letter. Keep it with the key files.",
        "Do not commit it. Do not copy it to artifacts or chat.",
        "",
    ]
    for name in names:
        path = directory / name
        lines.append(f"file.{name}={path.resolve() if path.exists() else 'MISSING'}")
    lines.append("")
    for name in names:
        path = directory / name
        lines.append(f"===== {name} =====")
        if path.exists():
            lines.append(path.read_text(encoding="utf-8").rstrip("\n"))
        else:
            lines.append("MISSING")
        lines.append("")
    letter = directory / WALLET_LETTER_NAME
    letter.write_text("\n".join(lines) + "\n", encoding="utf-8")
    letter.chmod(0o600)
    return letter


def ensure_demo_wallet(client: NodeClient, root: Path | None = None) -> dict[str, str]:
    directory = keys_dir(root)
    vkey = directory / "payment.vkey"
    skey = directory / "payment.skey"
    addr = directory / "payment.addr"
    stake_vkey = directory / "stake.vkey"
    stake_skey = directory / "stake.skey"
    stake_addr = directory / "stake.addr"

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
    if not stake_vkey.exists() or not stake_skey.exists():
        client.run_checked(
            [
                "latest",
                "stake-address",
                "key-gen",
                "--verification-key-file",
                str(stake_vkey),
                "--signing-key-file",
                str(stake_skey),
            ]
        )
    if not _read_text(stake_addr):
        client.run_checked(
            [
                "latest",
                "stake-address",
                "build",
                "--stake-verification-key-file",
                str(stake_vkey),
                "--testnet-magic",
                str(PREPROD_MAGIC),
                "--out-file",
                str(stake_addr),
            ]
        )

    address = _read_text(addr)
    if not address or _is_enterprise_test_address(address):
        client.run_checked(
            [
                "address",
                "build",
                "--payment-verification-key-file",
                str(vkey),
                "--stake-verification-key-file",
                str(stake_vkey),
                "--testnet-magic",
                str(PREPROD_MAGIC),
                "--out-file",
                str(addr),
            ]
        )
        address = _read_text(addr)

    if not address:
        raise NodeError("payment.addr is empty")
    if not address.startswith("addr_test"):
        raise NodeError("demo wallet is not a Preprod test address")
    reward = _read_text(stake_addr)
    if reward and not reward.startswith("stake_test"):
        raise NodeError("stake.addr is not a Preprod stake_test address")
    letter = write_wallet_letter(directory)
    return {
        "address": address,
        "stakeAddress": reward,
        "verificationKeyFile": str(vkey),
        "signingKeyFile": str(skey),
        "stakeVerificationKeyFile": str(stake_vkey),
        "stakeSigningKeyFile": str(stake_skey),
        "addressFile": str(addr),
        "stakeAddressFile": str(stake_addr),
        "walletLetterFile": str(letter),
    }


def utxo_lovelace(utxos: dict[str, Any] | None) -> int:
    total = 0
    if not utxos:
        return 0
    for utxo in utxos.values():
        if not isinstance(utxo, dict):
            continue
        value = utxo.get("value") or {}
        try:
            total += int(value.get("lovelace") or 0)
        except (TypeError, ValueError):
            continue
    return total
