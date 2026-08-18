# Govtools

This repository holds **three independent products**. They do not share Telegram bots, databases, or application code.

| Product | Company / job | Telegram | Folder |
| --- | --- | --- | --- |
| Mr North | TrueHold **crypto** alerts | none (webhook JSON) | [`mr_north/`](mr_north/) |
| Realtor acquisition | Property matching for one Nevada realtor | **@PirateEye_bot** | [`realtor-agent/`](realtor-agent/) |
| TrueHold Wellness | Order-email workflow | **@THWellness_bot** | [`truehold-wellness/`](truehold-wellness/) |

Never put the Wellness token in `realtor-agent/`. Never put the realtor token in `truehold-wellness/`. Live mode in each package calls Telegram `getMe` and refuses to start on the wrong username.

These three agents are **protected business infrastructure**. CI fails if one is deleted unless two different people complete `.github/DELETE_AGENT_CONFIRMATION.json`. See [`PROTECTED_AGENTS.md`](PROTECTED_AGENTS.md).

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

## Realtor Property Acquisition (@PirateEye_bot)

Self-contained in [`realtor-agent/`](realtor-agent/). Not TrueHold Wellness.

```bash
cd realtor-agent
python -m pip install -e ".[dev]"
cp .env.example .env
python -m app.cli demo
python -m pytest
```

## TrueHold Wellness order emails (@THWellness_bot)

Original inbox-snapshot agent, restored under [`truehold-wellness/`](truehold-wellness/). Spec: [`truehold-wellness/ORIGINAL_SPEC.md`](truehold-wellness/ORIGINAL_SPEC.md). Not realtor-agent. `@Npeppers_bot` was deleted and cannot be undeleted.

```bash
cd truehold-wellness
python -m pip install -e ".[dev]"
python -m wellness_agent compose
python -m wellness_agent send --dry-run --type order
python -m pytest
```

Telegram: **@THWellness_bot** (`/start`, `/inbox`, `/order`). Live `getMe` must return `THWellness_bot`.

## Tests

Root pytest is **Mr North only**:

```bash
python -m pytest
```

Realtor and Wellness each have their own install + pytest in their folders (and separate CI jobs).
