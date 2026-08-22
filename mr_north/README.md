# Agent North — market watcher

Telegram: **@Mr_North_bot** only.

This folder is the entire agent. Copy `mr_north/` to run it in its own Docker container. Nothing outside this directory is required.

North watches official and public market sources and delivers reports as soon as the print changes:

1. Immediate BTC alerts on a $65K watch-level cross or a ≥2% move (CoinGecko simple price: https://docs.coingecko.com/reference/simple-price).
2. Hourly Bureau of Labor Statistics breakdown (API v1: https://www.bls.gov/developers/api_signature.htm).
3. The larger geopolitical / market catalyst briefing, attached to every alert and also sent on its own.

Live `getMe` must return `Mr_North_bot`. Token env: `NORTH_TELEGRAM_BOT_TOKEN`.

Destinations (economics / trading only):

1. James personally — `NORTH_TELEGRAM_CHAT_ID` (default `1150046483`)
2. **MaximumMint & North** — `NORTH_TELEGRAM_GROUP_CHAT_ID` (bound by group title; fallback `-1003939359929`)

Never the PirateEye realtor group (`-5372586958`). Telegram sendMessage: https://core.telegram.org/bots/api#sendmessage

Bind the group: add **@Mr_North_bot** to MaximumMint & North (not MaximumMint & Agent Real), send any message in that group, then `python -m mr_north telegram-capture` or `python -m mr_north telegram-whoami`.

`python -m mr_north destinations` prints the live chat ids.

## Local

```bash
cd mr_north
python -m pip install -e ".[dev]"
cp .env.example .env
python -m mr_north telegram-whoami
python -m mr_north catalyst --dry-run
python -m mr_north hourly --dry-run
python -m mr_north watch --dry-run
python -m pytest
```

Live:

```bash
python -m mr_north catalyst
python -m mr_north hourly
python -m mr_north watch
python -m mr_north hourly-loop
bash scripts/keep_hourly.sh
```

Soul / timer: [`SOUL.md`](SOUL.md). Durable GitHub cron (after this package is on **main**): repo workflows `mr-north-hourly.yml` and `mr-north-watch.yml`.

## Docker

Image: https://hub.docker.com/_/python  
Dockerfile reference: https://docs.docker.com/reference/dockerfile/  
Compose: https://docs.docker.com/compose/

1. Copy `.env.example` to `.env` and set `NORTH_TELEGRAM_BOT_TOKEN` plus chat ids.
2. From this folder: `docker compose up --build`
3. The container runs `python -u -m mr_north hourly-loop` (catalyst on start, BLS every hour, BTC about every 5 minutes).

```bash
docker build -t agent-north .
docker compose up --build
```

Do not mount another agent’s `.env` into this container.
