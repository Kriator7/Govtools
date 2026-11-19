"""Query the local Preprod node over its Unix socket. Never Blockfrost, never mainnet."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from payment_app import PREPROD_MAGIC, PREPROD_NETWORK

FORBIDDEN_NETWORK_FLAGS = frozenset({"--mainnet"})
BLOCKFROST_ENV_KEYS = (
    "BLOCKFROST_API_KEY",
    "BLOCKFROST_PROJECT_ID",
    "BLOCKFROST_TOKEN",
)

CliRunner = Callable[[Sequence[str], Mapping[str, str], float], subprocess.CompletedProcess[str]]


class NodeError(RuntimeError):
    """cardano-cli or socket failure."""


class NodeNotReady(RuntimeError):
    """Preprod tip exists but the node is not fully synced."""


def parse_sync_progress(tip: Mapping[str, Any] | None) -> float | None:
    if not tip:
        return None
    raw = tip.get("syncProgress")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def is_preprod_ready(tip: Mapping[str, Any] | None) -> bool:
    progress = parse_sync_progress(tip)
    return progress is not None and progress >= 100.0


def default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_socket_path(root: Path | None = None) -> Path:
    override = os.environ.get("CARDANO_NODE_SOCKET_PATH")
    if override:
        return Path(override)
    return (root or default_root()) / "ipc" / "node.socket"


def resolve_cli(root: Path | None = None) -> str:
    override = os.environ.get("CARDANO_CLI")
    if override:
        return override
    local = (root or default_root()) / "bin" / "cardano-cli"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    found = shutil.which("cardano-cli")
    if found:
        return found
    raise NodeError(
        "cardano-cli not found. Run scripts/install_cli.sh or set CARDANO_CLI."
    )


def _scrub_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base if base is not None else os.environ)
    for key in BLOCKFROST_ENV_KEYS:
        env.pop(key, None)
    env["CARDANO_NODE_NETWORK_ID"] = str(PREPROD_MAGIC)
    return env


def _rewrite_socket_args(args: Sequence[str], socket_path: str) -> list[str]:
    out = list(args)
    if "--socket-path" in out:
        idx = out.index("--socket-path")
        if idx + 1 < len(out):
            out[idx + 1] = socket_path
    return out


def assert_preprod_args(args: Sequence[str]) -> None:
    for flag in FORBIDDEN_NETWORK_FLAGS:
        if flag in args:
            raise NodeError(f"refusing {flag}: this demo is Preprod only (magic {PREPROD_MAGIC})")
    if "--testnet-magic" in args:
        idx = list(args).index("--testnet-magic")
        if idx + 1 >= len(args) or str(args[idx + 1]) != str(PREPROD_MAGIC):
            raise NodeError(f"--testnet-magic must be {PREPROD_MAGIC} for Preprod")


def subprocess_runner(
    args: Sequence[str], env: Mapping[str, str], timeout: float
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        env=dict(env),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@dataclass
class NodeClient:
    socket_path: Path
    cli_path: str
    runner: CliRunner = field(default=subprocess_runner)
    timeout: float = 30.0

    @classmethod
    def from_env(cls, root: Path | None = None) -> "NodeClient":
        root = root or default_root()
        return cls(socket_path=default_socket_path(root), cli_path=resolve_cli(root))

    def run(self, args: Sequence[str], timeout: float | None = None) -> subprocess.CompletedProcess[str]:
        assert_preprod_args(args)
        env = _scrub_env()
        env["CARDANO_NODE_SOCKET_PATH"] = str(self.socket_path)
        cmd = [self.cli_path, *args]
        proc = self.runner(cmd, env, timeout or self.timeout)
        err = (proc.stderr or "").lower()
        if proc.returncode != 0 and "permission denied" in err:
            mapped = _rewrite_socket_args(args, "/ipc/node.socket")
            docker_cmd = [
                "docker",
                "exec",
                "-e",
                "CARDANO_NODE_SOCKET_PATH=/ipc/node.socket",
                "cardano-preprod-node",
                "cardano-cli",
                *mapped,
            ]
            return self.runner(docker_cmd, env, timeout or self.timeout)
        return proc

    def run_checked(self, args: Sequence[str], timeout: float | None = None) -> str:
        proc = self.run(args, timeout=timeout)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            raise NodeError(err or f"cardano-cli exited {proc.returncode}")
        return proc.stdout

    def query_tip(self) -> dict[str, Any]:
        if not self.socket_path.exists():
            raise NodeError(f"node socket not found: {self.socket_path}")
        stdout = self.run_checked(
            [
                "query",
                "tip",
                "--testnet-magic",
                str(PREPROD_MAGIC),
                "--socket-path",
                str(self.socket_path),
                "--output-json",
            ]
        )
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise NodeError(f"tip was not JSON: {stdout[:400]}") from exc
        if not isinstance(payload, dict):
            raise NodeError("tip JSON must be an object")
        return payload

    def query_utxo(self, address: str) -> dict[str, Any]:
        stdout = self.run_checked(
            [
                "query",
                "utxo",
                "--testnet-magic",
                str(PREPROD_MAGIC),
                "--socket-path",
                str(self.socket_path),
                "--address",
                address,
                "--output-json",
            ]
        )
        payload = json.loads(stdout)
        if not isinstance(payload, dict):
            raise NodeError("utxo JSON must be an object")
        return payload


def compose_state(root: Path | None = None) -> dict[str, Any]:
    """Read Docker Compose project state without treating 'running' as a synced node."""
    root = root or default_root()
    docker = shutil.which("docker") or "docker"
    cmd = [docker, "compose", "-f", str(root / "docker-compose.yml"), "ps", "--format", "json"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(root),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": str(exc), "services": []}
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return {"available": False, "error": err, "services": []}
    services: list[dict[str, Any]] = []
    raw = (proc.stdout or "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                services = parsed
            elif isinstance(parsed, dict):
                services = [parsed]
        except json.JSONDecodeError:
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    services.append(item)
    node = next((s for s in services if s.get("Service") == "cardano-node" or s.get("Name") == "cardano-preprod-node"), None)
    running = bool(node) and str(node.get("State") or "").lower() == "running"
    return {
        "available": True,
        "project": "cardano-preprod-demo",
        "nodeRunning": running,
        "node": node,
        "services": services,
        "error": None,
    }


def status_payload(
    client: NodeClient | None = None,
    root: Path | None = None,
    compose: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root or default_root()
    compose = compose if compose is not None else compose_state(root)
    socket_path = (client.socket_path if client else default_socket_path(root))
    payload: dict[str, Any] = {
        "network": PREPROD_NETWORK,
        "networkMagic": PREPROD_MAGIC,
        "provider": "local-node-socket",
        "blockfrost": False,
        "socketPath": str(socket_path),
        "socketExists": socket_path.exists(),
        "cliPath": client.cli_path if client else None,
        "compose": compose,
        "tip": None,
        "syncProgress": None,
        "ready": False,
        "sendEnabled": False,
        "error": None,
    }
    try:
        if client is None:
            client = NodeClient.from_env(root)
            payload["cliPath"] = client.cli_path
        tip = client.query_tip()
        payload["tip"] = tip
        payload["syncProgress"] = tip.get("syncProgress")
        payload["ready"] = is_preprod_ready(tip)
        payload["sendEnabled"] = payload["ready"]
    except (NodeError, OSError, subprocess.TimeoutExpired) as exc:
        payload["error"] = str(exc)
        payload["ready"] = False
        payload["sendEnabled"] = False
    return payload
