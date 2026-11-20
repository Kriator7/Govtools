#!/usr/bin/env bash
# Query Preprod tip through the node socket.
# CLI: cardano-cli query tip --testnet-magic 1 --socket-path ...
# Magic 1: image /opt/cardano/config/preprod/shelley-genesis.json networkMagic
#   and https://book.world.dev.cardano.org/env-preprod.html
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOCKET="${CARDANO_NODE_SOCKET_PATH:-$ROOT/ipc/node.socket}"
CLI="${CARDANO_CLI:-$ROOT/bin/cardano-cli}"

if [[ ! -x "$CLI" ]]; then
  echo "cardano-cli missing at $CLI" >&2
  echo "Run: bash $ROOT/scripts/install_cli.sh" >&2
  exit 1
fi

if [[ ! -S "$SOCKET" && ! -e "$SOCKET" ]]; then
  echo "node socket not found: $SOCKET" >&2
  echo "Compose state:" >&2
  docker compose -f "$ROOT/docker-compose.yml" ps || true
  echo "Recent node logs:" >&2
  docker compose -f "$ROOT/docker-compose.yml" logs --tail 80 cardano-node || true
  exit 1
fi

# Node creates the socket as root 0755; connecting needs write. Source: node log
# Startup.DiffusionInit.InsecureLocalSocket.Permissions mode 0o140755.
if [[ -S "$SOCKET" || -e "$SOCKET" ]]; then
  chmod 777 "$SOCKET" 2>/dev/null || true
fi

echo "cli: $(readlink -f "$CLI")"
echo "socket: $SOCKET"
"$CLI" --version
if ! "$CLI" query tip --testnet-magic 1 --socket-path "$SOCKET" --output-json; then
  echo "host socket connect failed; querying via the node container against /ipc/node.socket" >&2
  docker exec cardano-preprod-node cardano-cli query tip --testnet-magic 1 --socket-path /ipc/node.socket --output-json
fi
