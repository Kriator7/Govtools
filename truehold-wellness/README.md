# TrueHold Wellness — order email workflow

Self-contained **TrueHold Wellness** agent. Copy `truehold-wellness/` to move it. It does not import `realtor-agent/` or `mr_north/`.

| This package | Not this package |
| --- | --- |
| TrueHold Wellness order emails | Realtor property acquisition |
| Telegram **@Npeppers_bot** | Telegram **@PirateEye_bot** |
| `truehold-wellness/` | `realtor-agent/` |

Do not put a `@PirateEye_bot` token in this folder. Do not put a `@Npeppers_bot` token in `realtor-agent/`.

## Workflow

```
order email inbox → parse → order record → @Npeppers_bot operator alert
```

First milestone is local mocks (no live Gmail IMAP, no live Telegram token required).

```bash
cd truehold-wellness
python -m pip install -e ".[dev]"
cp .env.example .env
python -m thw.cli demo
python -m pytest
```

## Live Telegram (@Npeppers_bot only)

Source: https://core.telegram.org/bots/api

1. In `@BotFather`, open **Npeppers_bot** from `/mybots` (it must appear there).
2. Copy **API Token** from that screen, not from an old congratulations message.
3. Put it in `.env` as `TELEGRAM_MODE=live` and `TELEGRAM_BOT_TOKEN=…`. Never commit `.env`.
4. Live mode calls `getMe` and **refuses to start** unless the username is `Npeppers_bot`.
5. `python -m thw.cli telegram-poll` then send `/start` to https://t.me/Npeppers_bot
6. `python -m thw.cli ingest` to parse sample (or later, live) order emails and alert the operator.

A token that Telegram rejects as `401 Unauthorized` cannot run this bot. Recreate or refresh the token in `/mybots` first.

## Isolation

- Separate Python package (`thw`), database (`data/wellness.db`), env, tests, and CI job
- No shared models with realtor-agent
- Identity lock: forbidden username `PirateEye_bot`
