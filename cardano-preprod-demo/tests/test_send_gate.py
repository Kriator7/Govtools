from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from payment_app.node import NodeClient, NodeError, NodeNotReady
from payment_app.send import ada_to_lovelace, select_ada_inputs, send_ada


def test_selects_ada_only_inputs() -> None:
    utxos = {
        "aabb#0": {"value": {"lovelace": 2_000_000}},
        "aabb#1": {"value": {"lovelace": 5_000_000, "policy": {"asset": 1}}},
        "ccdd#0": {"value": {"lovelace": 4_000_000}},
    }
    chosen, total = select_ada_inputs(utxos, 3_000_000)
    assert chosen == ["ccdd#0"]
    assert total == 4_000_000


def test_amount_to_lovelace() -> None:
    assert ada_to_lovelace("1.5") == 1_500_000
    with pytest.raises(NodeError):
        ada_to_lovelace(0)


def test_send_refuses_until_preprod_ready(tmp_path: Path) -> None:
    socket = tmp_path / "node.socket"
    socket.write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(args, env, timeout):
        calls.append(list(args))
        return CompletedProcess(args, 0, stdout="{}", stderr="")

    client = NodeClient(socket_path=socket, cli_path="/opt/cardano-cli", runner=runner)
    with pytest.raises(NodeNotReady, match="sending is disabled"):
        send_ada(
            client,
            destination="addr_test1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq",
            ada_amount="1",
            tip={"syncProgress": "88.00"},
            root=tmp_path,
        )
    assert calls == []


def test_send_uses_node_socket_not_blockfrost(tmp_path: Path) -> None:
    socket = tmp_path / "node.socket"
    socket.write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(args, env, timeout):
        calls.append(list(args))
        assert "BLOCKFROST_API_KEY" not in env
        assert "--mainnet" not in args
        cmd = " ".join(args)
        if "address key-gen" in cmd:
            (tmp_path / "keys").mkdir(exist_ok=True)
            (tmp_path / "keys" / "payment.vkey").write_text("vkey", encoding="utf-8")
            (tmp_path / "keys" / "payment.skey").write_text("skey", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if "stake-address key-gen" in cmd:
            (tmp_path / "keys").mkdir(exist_ok=True)
            (tmp_path / "keys" / "stake.vkey").write_text("svkey", encoding="utf-8")
            (tmp_path / "keys" / "stake.skey").write_text("sskey", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if "stake-address build" in cmd:
            (tmp_path / "keys" / "stake.addr").write_text("stake_test1from", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if "address build" in cmd:
            (tmp_path / "keys" / "payment.addr").write_text("addr_test1qfrom", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if args[1:3] == ["query", "utxo"]:
            return CompletedProcess(
                args,
                0,
                stdout='{"aa#0": {"value": {"lovelace": 5000000}}}',
                stderr="",
            )
        if "transaction build" in cmd:
            (tmp_path / "keys" / "tx.raw").write_text("raw", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if "transaction sign" in cmd:
            (tmp_path / "keys" / "tx.signed").write_text("signed", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if "transaction submit" in cmd:
            return CompletedProcess(args, 0, stdout="Transaction successfully submitted.", stderr="")
        if "transaction txid" in cmd:
            return CompletedProcess(args, 0, stdout="deadbeef\n", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="unexpected " + cmd)

    client = NodeClient(socket_path=socket, cli_path="/opt/cardano-cli", runner=runner)
    result = send_ada(
        client,
        destination="addr_test1qto",
        ada_amount="1",
        tip={"syncProgress": "100.00"},
        root=tmp_path,
    )
    assert result["ok"] is True
    assert result["txId"] == "deadbeef"
    assert result["provider"] == "local-node-socket"
    joined = "\n".join(" ".join(c) for c in calls)
    assert "--testnet-magic 1" in joined
    assert f"--socket-path {socket}" in joined
    assert "blockfrost" not in joined.lower()
    assert "--mainnet" not in joined
