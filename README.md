# Govtools

This repo contains **Mr North**, the TrueHold crypto agent.

TrueHold Wellness is a separate, already-working agent. It is not in this repository and must not be modified here.

## Mr North (TrueHold crypto)

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

## Realtor Property Acquisition Automation

A separate, self-contained agent lives in [`realtor-agent/`](realtor-agent/). It is not part of Mr North. Copy that folder to move the realtor system; all of its code, templates, mappings, tests, and Docker files stay together.

```bash
cd realtor-agent
python -m pip install -e ".[dev]"
python -m app.cli demo
python -m pytest
```

## Tests

```bash
python -m pytest
```
