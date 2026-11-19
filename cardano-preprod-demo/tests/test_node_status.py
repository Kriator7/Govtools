from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from payment_app.node import (
    NodeClient,
    NodeError,
    assert_preprod_args,
    is_preprod_ready,
    parse_sync_progress,
    status_payload,
)


def test_ready_only_at_one_hundred() -> None:
    assert is_preprod_ready({"syncProgress": "100.00"}) is True
    assert is_preprod_ready({"syncProgress": "100"}) is True
    assert is_preprod_ready({"syncProgress": "99.99"}) is False
    assert is_preprod_ready({"syncProgress": "12.50"}) is False
    assert is_preprod_ready({}) is False
    assert is_preprod_ready(None) is False
    assert parse_sync_progress({"syncProgress": "not-a-number"}) is None


def test_refuses_mainnet_flag() -> None:
    with pytest.raises(NodeError, match="Preprod only"):
        assert_preprod_args(["query", "tip", "--mainnet"])
    with pytest.raises(NodeError, match="must be 1"):
        assert_preprod_args(["query", "tip", "--testnet-magic", "2"])
    assert_preprod_args(["query", "tip", "--testnet-magic", "1"])


def test_query_tip_uses_socket_and_magic(tmp_path: Path) -> None:
    socket = tmp_path / "node.socket"
    socket.write_text("", encoding="utf-8")
    seen: dict[str, object] = {}

    def runner(args, env, timeout):
        seen["args"] = list(args)
        seen["env"] = dict(env)
        seen["timeout"] = timeout
        return CompletedProcess(
            args,
            0,
            stdout=json.dumps(
                {
                    "block": 10,
                    "epoch": 4,
                    "era": "Conway",
                    "hash": "abc",
                    "slot": 99,
                    "syncProgress": "7.25",
                }
            ),
            stderr="",
        )

    client = NodeClient(socket_path=socket, cli_path="/opt/cardano-cli", runner=runner)
    tip = client.query_tip()
    assert tip["syncProgress"] == "7.25"
    args = seen["args"]
    assert args[0] == "/opt/cardano-cli"
    assert args[1:3] == ["query", "tip"]
    assert "--testnet-magic" in args
    assert args[args.index("--testnet-magic") + 1] == "1"
    assert "--socket-path" in args
    assert args[args.index("--socket-path") + 1] == str(socket)
    assert "--mainnet" not in args
    env = seen["env"]
    assert env["CARDANO_NODE_SOCKET_PATH"] == str(socket)
    assert env["CARDANO_NODE_NETWORK_ID"] == "1"
    assert "BLOCKFROST_API_KEY" not in env
    assert "BLOCKFROST_PROJECT_ID" not in env


def test_permission_denied_falls_back_to_docker_exec(tmp_path: Path) -> None:
    socket = tmp_path / "node.socket"
    socket.write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(args, env, timeout):
        calls.append(list(args))
        if args[0] == "/opt/cardano-cli":
            return CompletedProcess(
                args, 1, stdout="", stderr="Network.Socket.connect: permission denied"
            )
        return CompletedProcess(
            args, 0, stdout=json.dumps({"syncProgress": "3.00", "slot": 12}), stderr=""
        )

    client = NodeClient(socket_path=socket, cli_path="/opt/cardano-cli", runner=runner)
    tip = client.query_tip()
    assert tip["syncProgress"] == "3.00"
    assert calls[0][0] == "/opt/cardano-cli"
    assert calls[1][:3] == ["docker", "exec", "-e"]
    assert "cardano-preprod-node" in calls[1]
    assert calls[1][calls[1].index("--socket-path") + 1] == "/ipc/node.socket"
    assert calls[1][calls[1].index("--testnet-magic") + 1] == "1"


def test_status_payload_disables_send_while_syncing(tmp_path: Path) -> None:
    socket = tmp_path / "node.socket"
    socket.write_text("", encoding="utf-8")

    def runner(args, env, timeout):
        return CompletedProcess(
            args,
            0,
            stdout=json.dumps({"syncProgress": "41.10", "era": "Shelley", "slot": 1}),
            stderr="",
        )

    client = NodeClient(socket_path=socket, cli_path="/opt/cardano-cli", runner=runner)
    payload = status_payload(
        client,
        root=tmp_path,
        compose={"available": True, "project": "cardano-preprod-demo", "nodeRunning": True},
    )
    assert payload["network"] == "preprod"
    assert payload["networkMagic"] == 1
    assert payload["blockfrost"] is False
    assert payload["provider"] == "local-node-socket"
    assert payload["ready"] is False
    assert payload["sendEnabled"] is False
    assert payload["syncProgress"] == "41.10"
