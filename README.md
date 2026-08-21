# Govtools

This repository holds **three independent products**. They do not share Telegram bots, databases, or application code.

| Product | Company / job | Telegram | Folder |
| --- | --- | --- | --- |
| Mr North | TrueHold **crypto** alerts + hourly BLS | **@Mr_North_bot** | [`mr_north/`](mr_north/) |
| Realtor acquisition | Property matching for one Nevada realtor | **@PirateEye_bot** | [`realtor-agent/`](realtor-agent/) |
| TrueHold Wellness | Order-email workflow | **@THWellness_bot** | [`truehold-wellness/`](truehold-wellness/) |

Never put the Wellness token in `realtor-agent/` or `mr_north/`. Never put the realtor token in `truehold-wellness/` or `mr_north/`. Live `getMe` must return `@Mr_North_bot`, `@THWellness_bot`, or `@PirateEye_bot` for that package.

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
NORTH_TELEGRAM_BOT_TOKEN=... NORTH_TELEGRAM_CHAT_ID=... python -m mr_north send --type btc_threshold
```

`send` drops the text on **@Mr_North_bot** to **both** configured Telegram chats (`NORTH_TELEGRAM_CHAT_ID` and `NORTH_TELEGRAM_GROUP_CHAT_ID`, default `-1003939359929`) and may also POST JSON to `ALERT_WEBHOOK_URL`. Do not use the PirateEye group.

### Hourly Bureau of Labor Statistics breakdown + immediate watch

The hourly BLS print and the larger catalyst briefing are **North's job**. He fetches official series, watches BTC for $65K / ≥2% moves, and drops both report types in **both** North chats (not @THWellness_bot, not @PirateEye_bot).

```bash
python -m mr_north hourly --dry-run
python -m mr_north hourly
python -m mr_north catalyst
python -m mr_north watch
python -m mr_north hourly-status
python -m mr_north telegram-whoami
python -m mr_north telegram-capture
bash mr_north/scripts/keep_hourly.sh
```

Soul / timer contract: [`mr_north/SOUL.md`](mr_north/SOUL.md). Durable cron: `.github/workflows/mr-north-hourly.yml` (`7 * * * *` UTC) and `.github/workflows/mr-north-watch.yml` (`*/15 * * * *`). GitHub only runs scheduled workflows on **main** after merge. Set repository secrets `NORTH_TELEGRAM_BOT_TOKEN` and `NORTH_TELEGRAM_CHAT_ID` (second location). Group default is `-1003939359929`. BLS API: https://www.bls.gov/developers/api_signature.htm — Telegram: https://core.telegram.org/bots/api#sendmessage

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

Telegram: **@THWellness_bot** (`/start`, `/inbox`, `/catalog`, `/product`, `/order`). Live `getMe` must return `THWellness_bot`. Inventory PDFs live in `truehold-wellness/wellness_agent/inventory/pdfs/`.

## Tests

Root pytest is **Mr North only**:

```bash
python -m pytest
```

Realtor and Wellness each have their own install + pytest in their folders (and separate CI jobs).
