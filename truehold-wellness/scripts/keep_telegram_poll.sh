#!/usr/bin/env bash
# Outer keeper for @THWellness_bot. If the Python process exits, start it again.
# Telegram getUpdates: https://core.telegram.org/bots/api#getupdates
# Only one of these should run. python -m wellness_agent telegram-poll also
# restarts the inner poll loop; this wrapper covers interpreter crashes.
set -u
cd "$(dirname "$0")/.."
while true; do
  python3 -u -m wellness_agent telegram-poll
  code=$?
  printf '%s\n' "{\"ok\":false,\"restarting\":true,\"exit\":${code},\"bot\":\"@THWellness_bot\"}"
  sleep 2
done
