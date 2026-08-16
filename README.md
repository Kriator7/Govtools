# Govtools

TrueHold crypto agent lives in `truehold/crypto_agent`. When any alert fires, the outbound message and JSON payload also include the current geopolitical / market catalyst briefing.

## What gets sent

Every alert contains:

1. The trigger that fired (BTC threshold, capital-regime, Macro Liquidity, business inbox, or a manual/geopolitical catalyst alert).
2. The current catalyst briefing: Strait of Hormuz / Iran pressure, money-flow implications, crypto status, TrueHold Wellness inbox status, and the oil–yields–DXY watch.

The briefing is stored in `truehold/crypto_agent/data/current_catalyst.json` and is attached automatically. You do not pass it per send.

## Run

```bash
python -m pip install -e ".[dev]"
python -m truehold.crypto_agent compose
python -m truehold.crypto_agent compose --type btc_threshold --detail "BTC crossed the $65K watch level."
python -m truehold.crypto_agent send --dry-run
ALERT_WEBHOOK_URL=https://example.invalid/alerts python -m truehold.crypto_agent send --type btc_threshold
```

`send` POSTs JSON with `trigger`, `catalyst`, and `text`. `compose --json` prints that payload without delivering it.

## Tests

```bash
python -m pytest
```
