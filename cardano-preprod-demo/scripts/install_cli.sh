#!/usr/bin/env bash
# Official IntersectMBO cardano-node 11.1.3 linux-amd64 tarball.
# Release: https://github.com/IntersectMBO/cardano-node/releases/tag/11.1.3
# sha256sums: https://github.com/IntersectMBO/cardano-node/releases/download/11.1.3/cardano-node-11.1.3-sha256sums.txt
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="11.1.3"
ARCHIVE="cardano-node-${VERSION}-linux-amd64.tar.gz"
URL="https://github.com/IntersectMBO/cardano-node/releases/download/${VERSION}/${ARCHIVE}"
SHA256="530fb99986fbdccc46f9ee0dd86cabb1393b015feac9173cb731d89fa748365f"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

mkdir -p "$ROOT/bin"
if [[ -x "$ROOT/bin/cardano-cli" ]]; then
  echo "cardano-cli already at $ROOT/bin/cardano-cli"
  "$ROOT/bin/cardano-cli" version || "$ROOT/bin/cardano-cli" --version
  exit 0
fi

curl -L --fail -o "$WORKDIR/$ARCHIVE" "$URL"
echo "${SHA256}  $WORKDIR/$ARCHIVE" | sha256sum -c -
tar -xzf "$WORKDIR/$ARCHIVE" -C "$WORKDIR"
install -m 0755 "$WORKDIR/bin/cardano-cli" "$ROOT/bin/cardano-cli"
echo "installed $(readlink -f "$ROOT/bin/cardano-cli")"
"$ROOT/bin/cardano-cli" --version
