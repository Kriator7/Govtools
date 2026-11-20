#!/usr/bin/env bash
# Bootstrap the Preprod node DB from the official Mithril snapshot.
#
# This is TESTNET / Preprod only (networkMagic 1). The script hardcodes the
# release-preprod aggregator and refuses mainnet endpoints.
#
# Sources:
#   Bootstrap: https://mithril.network/doc/manual/getting-started/bootstrap-cardano-node
#   Aggregator: https://aggregator.release-preprod.api.mithril.network/aggregator
#   Vkeys: https://github.com/IntersectMBO/mithril/tree/main/mithril-infra/configuration/release-preprod
#   Client install: https://raw.githubusercontent.com/IntersectMBO/mithril/main/mithril-install.sh
#   Distribution pin: https://github.com/IntersectMBO/mithril/releases/tag/2642.0
#     mithril-client 0.13.29+e85df3d (linux-x64 tarball)
#
# Usage (from cardano-preprod-demo/):
#   bash scripts/mithril_bootstrap.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PREPROD_AGGREGATOR="https://aggregator.release-preprod.api.mithril.network/aggregator"
PREPROD_GENESIS_VKEY_URL="https://raw.githubusercontent.com/IntersectMBO/mithril/main/mithril-infra/configuration/release-preprod/genesis.vkey"
PREPROD_ANCILLARY_VKEY_URL="https://raw.githubusercontent.com/IntersectMBO/mithril/main/mithril-infra/configuration/release-preprod/ancillary.vkey"
MITHRIL_DISTRIBUTION="2642.0"
VOLUME_NAME="cardano-preprod-node-db"
DOWNLOAD_DIR="${MITHRIL_DOWNLOAD_DIR:-${TMPDIR:-/var/tmp}/mithril-preprod}"
INSTALL_PREFIX="${MITHRIL_INSTALL_PREFIX:-$HOME/.local/bin}"

if [[ "${CARDANO_NETWORK:-preprod}" != "preprod" ]]; then
  echo "This demo is Preprod only. Refusing CARDANO_NETWORK=${CARDANO_NETWORK}." >&2
  exit 1
fi
if [[ "${AGGREGATOR_ENDPOINT:-$PREPROD_AGGREGATOR}" == *mainnet* ]]; then
  echo "Refusing mainnet Mithril aggregator: ${AGGREGATOR_ENDPOINT}" >&2
  exit 1
fi

export CARDANO_NETWORK=preprod
export AGGREGATOR_ENDPOINT="$PREPROD_AGGREGATOR"

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not reachable. Start dockerd first." >&2
  exit 1
fi

mkdir -p "$INSTALL_PREFIX"
export PATH="$INSTALL_PREFIX:$PATH"

if ! command -v mithril-client >/dev/null 2>&1; then
  echo "Installing mithril-client from IntersectMBO distribution ${MITHRIL_DISTRIBUTION}..."
  curl --proto '=https' --tlsv1.2 --fail -sSf \
    https://raw.githubusercontent.com/IntersectMBO/mithril/main/mithril-install.sh \
    | sh -s -- -c mithril-client -d "$MITHRIL_DISTRIBUTION" -p "$INSTALL_PREFIX"
fi

mithril-client -V

echo "Fetching release-preprod verification keys..."
export GENESIS_VERIFICATION_KEY
GENESIS_VERIFICATION_KEY="$(curl --proto '=https' --tlsv1.2 --fail -sSf "$PREPROD_GENESIS_VKEY_URL")"
export ANCILLARY_VERIFICATION_KEY
ANCILLARY_VERIFICATION_KEY="$(curl --proto '=https' --tlsv1.2 --fail -sSf "$PREPROD_ANCILLARY_VKEY_URL")"
if [[ -z "$GENESIS_VERIFICATION_KEY" || -z "$ANCILLARY_VERIFICATION_KEY" ]]; then
  echo "Failed to load Preprod Mithril verification keys." >&2
  exit 1
fi

echo "Listing certified Preprod snapshots from ${AGGREGATOR_ENDPOINT}..."
mithril-client cardano-db snapshot list | head -n 20

mkdir -p "$DOWNLOAD_DIR"
echo "Downloading latest Preprod snapshot (with ancillary ledger files) to ${DOWNLOAD_DIR}..."
mithril-client cardano-db download --include-ancillary --download-dir "$DOWNLOAD_DIR" latest

DB_DIR="$DOWNLOAD_DIR/db"
if [[ ! -d "$DB_DIR/immutable" || ! -d "$DB_DIR/ledger" ]]; then
  echo "Mithril unpack did not produce immutable/ledger under ${DB_DIR}." >&2
  exit 1
fi
MAGIC="$(tr -d '[:space:]' < "$DB_DIR/protocolMagicId")"
if [[ "$MAGIC" != "1" ]]; then
  echo "Snapshot protocolMagicId=${MAGIC} is not Preprod (expected 1). Refusing DB swap." >&2
  exit 1
fi

echo "Stopping Preprod node before replacing ${VOLUME_NAME}..."
docker compose -f "$ROOT/docker-compose.yml" stop cardano-node

if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
  docker compose -f "$ROOT/docker-compose.yml" up --no-start cardano-node
fi

MOUNTPOINT="$(docker volume inspect "$VOLUME_NAME" --format '{{.Mountpoint}}')"
if [[ -z "$MOUNTPOINT" || ! -d "$MOUNTPOINT" ]]; then
  echo "Could not resolve Docker volume mountpoint for ${VOLUME_NAME}." >&2
  exit 1
fi

SUDO=()
if [[ ! -w "$MOUNTPOINT" ]]; then
  SUDO=(sudo)
fi

echo "Replacing ${MOUNTPOINT} with verified Mithril db (protocolMagicId=1)..."
"${SUDO[@]}" find "$MOUNTPOINT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
"${SUDO[@]}" cp -a "$DB_DIR"/. "$MOUNTPOINT"/
"${SUDO[@]}" chmod -R a+rX "$MOUNTPOINT"

echo "Starting Preprod node..."
docker compose -f "$ROOT/docker-compose.yml" start cardano-node || \
  docker compose -f "$ROOT/docker-compose.yml" up -d cardano-node

echo "Waiting for node socket..."
SOCKET="$ROOT/ipc/node.socket"
for _ in $(seq 1 60); do
  if [[ -S "$SOCKET" || -e "$SOCKET" ]]; then
    chmod 777 "$SOCKET" 2>/dev/null || true
    break
  fi
  sleep 2
done

if [[ -x "$ROOT/scripts/query_tip.sh" ]]; then
  bash "$ROOT/scripts/query_tip.sh" || true
fi

echo "Mithril Preprod bootstrap finished. Volume ${VOLUME_NAME} now holds the certified snapshot."
echo "Send stays gated in the payment GUI until cardano-cli reports syncProgress 100.00."
