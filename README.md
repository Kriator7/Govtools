# Govtools

This repository holds two **separate** TrueHold agents. Do not mix their alerts, tokens, or webhooks.

## TrueHold Wellness — @THWellness_bot

Source: `truehold-wellness/`

Telegram shop/order bot. Keep-alive: `bash truehold-wellness/scripts/keep_telegram_poll.sh` (only one copy). Token is `TELEGRAM_BOT_TOKEN` in `truehold-wellness/.env` (not committed).

```bash
cd truehold-wellness
python -m pip install -e ".[dev]"
python -m wellness_agent whoami
python -m wellness_agent telegram-status
```

## Mr North (TrueHold crypto)

Source: `mr_north/`

When any Mr North alert fires, the outbound message and JSON payload also include the current geopolitical / market catalyst briefing:


1. The crypto trigger (BTC threshold, capital-regime, Macro Liquidity, or a manual/geopolitical catalyst alert).
2. The catalyst briefing: Strait of Hormuz / Iran pressure, money-flow implications, crypto status, and the oil–yields–DXY watch.

The briefing is stored in `mr_north/data/current_catalyst.json` and is attached automatically.

```bash
python -m pip install -e ".[dev]"
python -m mr_north compose
python -m mr_north compose --type btc_threshold --detail "BTC crossed the $65K watch level."
python -m mr_north send --dry-run
ALERT_WEBHOOK_URL=https://example.invalid/alerts python -m mr_north send --type btc_threshold
```

`send` POSTs JSON with `agent=mr-north`, `trigger`, `catalyst`, and `text`.

## Tests

```bash
python -m pytest
cd truehold-wellness && python -m pytest
```
