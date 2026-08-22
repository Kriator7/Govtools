#!/usr/bin/env bash
# Outer keeper for Agent North: catalyst, hourly BLS, immediate BTC watch.
# If the Python loop exits, start it again. Only one copy should run.
set -u
cd "$(dirname "$0")/.."
while true; do
  python3 -u -m mr_north hourly-loop
  code=$?
  printf '%s\n' "{\"ok\":false,\"restarting\":true,\"exit\":${code},\"agent\":\"mr-north\",\"job\":\"hourly-bls\"}"
  sleep 5
done
