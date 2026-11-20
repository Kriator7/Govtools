#!/usr/bin/env bash
# Build a Preprod payment+stake wallet with cardano-cli.
#
# Sources:
#   https://docs.cardano.org/cardano-testnets/getting-started
#   https://developers.cardano.org/docs/operate-a-stake-pool/block-producer/generating-wallet-keys/
# Magic 1 = Preprod. Never --mainnet.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEYS="$ROOT/keys"
CLI="${CARDANO_CLI:-$ROOT/bin/cardano-cli}"
MAGIC=1

if [[ ! -x "$CLI" ]]; then
  echo "cardano-cli missing at $CLI" >&2
  echo "Run: bash $ROOT/scripts/install_cli.sh" >&2
  exit 1
fi

mkdir -p "$KEYS"
chmod 700 "$KEYS"

if [[ ! -f "$KEYS/payment.skey" || ! -f "$KEYS/payment.vkey" ]]; then
  "$CLI" address key-gen \
    --verification-key-file "$KEYS/payment.vkey" \
    --signing-key-file "$KEYS/payment.skey"
fi

if [[ ! -f "$KEYS/stake.skey" || ! -f "$KEYS/stake.vkey" ]]; then
  "$CLI" latest stake-address key-gen \
    --verification-key-file "$KEYS/stake.vkey" \
    --signing-key-file "$KEYS/stake.skey"
fi

"$CLI" latest stake-address build \
  --stake-verification-key-file "$KEYS/stake.vkey" \
  --testnet-magic "$MAGIC" \
  --out-file "$KEYS/stake.addr"

"$CLI" address build \
  --payment-verification-key-file "$KEYS/payment.vkey" \
  --stake-verification-key-file "$KEYS/stake.vkey" \
  --testnet-magic "$MAGIC" \
  --out-file "$KEYS/payment.addr"

chmod 600 "$KEYS"/*.skey "$KEYS"/*.vkey "$KEYS"/*.addr 2>/dev/null || true

# Wallet letter: one file that holds the Preprod addresses and key material.
# Gitignored. Do not echo signing-key contents to the terminal.
LETTER="$KEYS/wallet-letter.txt"
umask 077
{
  echo "Cardano Preprod wallet letter"
  echo "network=preprod"
  echo "networkMagic=1"
  echo "sources=https://docs.cardano.org/cardano-testnets/getting-started"
  echo "directory=$KEYS"
  echo
  echo "This file is the wallet letter. Keep it with the key files."
  echo "Do not commit it. Do not copy it to artifacts or chat."
  echo
  for name in payment.addr stake.addr payment.vkey stake.vkey payment.skey stake.skey; do
    echo "file.${name}=$KEYS/$name"
  done
  echo
  for name in payment.addr stake.addr payment.vkey stake.vkey payment.skey stake.skey; do
    echo "===== ${name} ====="
    if [[ -f "$KEYS/$name" ]]; then
      cat "$KEYS/$name"
      echo
    else
      echo "MISSING"
    fi
    echo
  done
} > "$LETTER"
chmod 600 "$LETTER"

echo "payment.addr=$(tr -d '[:space:]' < "$KEYS/payment.addr")"
echo "stake.addr=$(tr -d '[:space:]' < "$KEYS/stake.addr")"
echo "wallet.letter=$LETTER"
"$CLI" address info --address "$(tr -d '[:space:]' < "$KEYS/payment.addr")"
