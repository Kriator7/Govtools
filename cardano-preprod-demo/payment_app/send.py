"""Build and submit a Preprod payment through the local node socket."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from payment_app import PREPROD_MAGIC
from payment_app.node import NodeClient, NodeError, NodeNotReady, is_preprod_ready
from payment_app.wallet import ensure_demo_wallet, keys_dir

LOVELACE_PER_ADA = 1_000_000


def ada_to_lovelace(amount: str | float | int) -> int:
    lovelace = int(round(float(amount) * LOVELACE_PER_ADA))
    if lovelace <= 0:
        raise NodeError("amount must be greater than 0 ADA")
    return lovelace


def _ada_lovelace(utxo: dict[str, Any]) -> int:
    value = utxo.get("value") or {}
    ada = value.get("lovelace", 0)
    try:
        return int(ada)
    except (TypeError, ValueError):
        return 0


def select_ada_inputs(utxos: dict[str, Any], needed: int) -> tuple[list[str], int]:
    spendable: list[tuple[str, int]] = []
    for tx_in, utxo in utxos.items():
        if not isinstance(utxo, dict):
            continue
        value = utxo.get("value") or {}
        extra = {k: v for k, v in value.items() if k != "lovelace"}
        if extra:
            continue
        amount = _ada_lovelace(utxo)
        if amount > 0:
            spendable.append((tx_in, amount))
    spendable.sort(key=lambda item: item[1], reverse=True)
    selected: list[str] = []
    total = 0
    for tx_in, amount in spendable:
        selected.append(tx_in)
        total += amount
        if total >= needed:
            break
    if total < needed:
        raise NodeError(
            f"insufficient ADA-only UTxO: have {total} lovelace, need {needed}"
        )
    return selected, total


def send_ada(
    client: NodeClient,
    destination: str,
    ada_amount: str | float | int,
    *,
    tip: dict[str, Any] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    destination = (destination or "").strip()
    if not destination.startswith("addr_test"):
        raise NodeError("destination must be a Preprod addr_test address")
    if tip is None:
        tip = client.query_tip()
    if not is_preprod_ready(tip):
        progress = tip.get("syncProgress") if tip else None
        raise NodeNotReady(
            f"Preprod is not ready (syncProgress={progress!r}); sending is disabled"
        )

    wallet = ensure_demo_wallet(client, root)
    lovelace = ada_to_lovelace(ada_amount)
    utxos = client.query_utxo(wallet["address"])
    tx_ins, _total = select_ada_inputs(utxos, lovelace)

    work = keys_dir(root)
    raw = work / "tx.raw"
    signed = work / "tx.signed"
    for path in (raw, signed):
        if path.exists():
            path.unlink()

    build_args = [
        "conway",
        "transaction",
        "build",
        "--testnet-magic",
        str(PREPROD_MAGIC),
        "--socket-path",
        str(client.socket_path),
    ]
    for tx_in in tx_ins:
        build_args.extend(["--tx-in", tx_in])
    build_args.extend(
        [
            "--tx-out",
            f"{destination}+{lovelace}",
            "--change-address",
            wallet["address"],
            "--out-file",
            str(raw),
        ]
    )
    client.run_checked(build_args)

    client.run_checked(
        [
            "conway",
            "transaction",
            "sign",
            "--testnet-magic",
            str(PREPROD_MAGIC),
            "--tx-body-file",
            str(raw),
            "--signing-key-file",
            wallet["signingKeyFile"],
            "--out-file",
            str(signed),
        ]
    )

    submit_out = client.run_checked(
        [
            "conway",
            "transaction",
            "submit",
            "--testnet-magic",
            str(PREPROD_MAGIC),
            "--socket-path",
            str(client.socket_path),
            "--tx-file",
            str(signed),
        ]
    )
    txid = client.run_checked(
        ["conway", "transaction", "txid", "--tx-file", str(signed)]
    ).strip()
    return {
        "ok": True,
        "txId": txid,
        "submit": submit_out.strip(),
        "inputs": tx_ins,
        "lovelace": lovelace,
        "from": wallet["address"],
        "to": destination,
        "provider": "local-node-socket",
    }


def send_error_payload(exc: Exception, tip: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "error": str(exc),
        "ready": is_preprod_ready(tip),
        "syncProgress": None if tip is None else tip.get("syncProgress"),
        "provider": "local-node-socket",
        "blockfrost": False,
    }
