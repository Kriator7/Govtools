from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

from payment_app.node import NodeClient
from payment_app.wallet import ensure_demo_wallet, utxo_lovelace


def test_builds_preprod_base_address(tmp_path: Path) -> None:
    socket = tmp_path / "node.socket"
    socket.write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(args, env, timeout):
        calls.append(list(args))
        assert "--mainnet" not in args
        cmd = " ".join(args)
        keys = tmp_path / "keys"
        keys.mkdir(exist_ok=True)
        if "address key-gen" in cmd:
            (keys / "payment.vkey").write_text("vkey", encoding="utf-8")
            (keys / "payment.skey").write_text("skey", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if "stake-address key-gen" in cmd:
            (keys / "stake.vkey").write_text("svkey", encoding="utf-8")
            (keys / "stake.skey").write_text("sskey", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if "stake-address build" in cmd:
            assert "--testnet-magic" in args
            assert args[args.index("--testnet-magic") + 1] == "1"
            (keys / "stake.addr").write_text("stake_test1abc", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if "address build" in cmd:
            assert "--stake-verification-key-file" in args
            assert "--testnet-magic" in args
            assert args[args.index("--testnet-magic") + 1] == "1"
            (keys / "payment.addr").write_text("addr_test1qabc", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="unexpected " + cmd)

    client = NodeClient(socket_path=socket, cli_path="/opt/cardano-cli", runner=runner)
    wallet = ensure_demo_wallet(client, tmp_path)
    assert wallet["address"] == "addr_test1qabc"
    assert wallet["stakeAddress"] == "stake_test1abc"
    joined = "\n".join(" ".join(c) for c in calls)
    assert "address key-gen" in joined
    assert "stake-address key-gen" in joined
    assert "--testnet-magic 1" in joined
    assert "--mainnet" not in joined


def test_upgrades_enterprise_address_to_base(tmp_path: Path) -> None:
    socket = tmp_path / "node.socket"
    socket.write_text("", encoding="utf-8")
    keys = tmp_path / "keys"
    keys.mkdir()
    (keys / "payment.vkey").write_text("vkey", encoding="utf-8")
    (keys / "payment.skey").write_text("skey", encoding="utf-8")
    (keys / "payment.addr").write_text(
        "addr_test1vp6lhzr460aw2eg7tq4gsl97szqw83h3hfkt7m3xqf08vqca9pule",
        encoding="utf-8",
    )

    def runner(args, env, timeout):
        cmd = " ".join(args)
        if "stake-address key-gen" in cmd:
            (keys / "stake.vkey").write_text("svkey", encoding="utf-8")
            (keys / "stake.skey").write_text("sskey", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if "stake-address build" in cmd:
            (keys / "stake.addr").write_text("stake_test1xyz", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        if "address build" in cmd:
            (keys / "payment.addr").write_text("addr_test1qbase", encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="unexpected " + cmd)

    client = NodeClient(socket_path=socket, cli_path="/opt/cardano-cli", runner=runner)
    wallet = ensure_demo_wallet(client, tmp_path)
    assert wallet["address"] == "addr_test1qbase"


def test_utxo_lovelace_sums_ada_only() -> None:
    assert utxo_lovelace({}) == 0
    assert (
        utxo_lovelace(
            {
                "aa#0": {"value": {"lovelace": 1_000_000}},
                "aa#1": {"value": {"lovelace": 2_500_000, "policy": {"a": 1}}},
            }
        )
        == 3_500_000
    )
