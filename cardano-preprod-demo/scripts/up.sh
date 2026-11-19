#!/usr/bin/env bash
# Start the official Preprod node (NETWORK=preprod, persistent DB volume) and the payment GUI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p ipc keys
chmod 777 ipc

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not reachable. Start dockerd first." >&2
  exit 1
fi

echo "Compose projects before start:"
docker compose ls -a || true
docker compose -f "$ROOT/docker-compose.yml" ps || true

# Official compose path: NETWORK=preprod is hardcoded in docker-compose.yml.
docker compose -f "$ROOT/docker-compose.yml" up -d

echo "Compose projects after start:"
docker compose ls -a
docker compose -f "$ROOT/docker-compose.yml" ps

bash "$ROOT/scripts/install_cli.sh"
export CARDANO_NODE_SOCKET_PATH="$ROOT/ipc/node.socket"
export CARDANO_CLI="$ROOT/bin/cardano-cli"
export PYTHONPATH="$ROOT"

# Socket can take a few seconds after the container starts.
for _ in $(seq 1 30); do
  if [[ -S "$CARDANO_NODE_SOCKET_PATH" || -e "$CARDANO_NODE_SOCKET_PATH" ]]; then
    chmod 777 "$CARDANO_NODE_SOCKET_PATH" 2>/dev/null || true
    break
  fi
  sleep 1
done

if ! bash "$ROOT/scripts/query_tip.sh"; then
  echo "Tip query failed. Node logs:" >&2
  docker compose -f "$ROOT/docker-compose.yml" logs --tail 120 cardano-node >&2 || true
fi

exec python3 -m payment_app
