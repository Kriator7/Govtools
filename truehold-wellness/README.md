# TrueHold Wellness — business inbox + @Npeppers_bot

Self-contained **TrueHold Wellness** agent restored from the original inbox-snapshot design (orders, payments, fulfillment, shipping, cancellations, peptides). Copy `truehold-wellness/` to move it.

It does **not** import `realtor-agent/` or `mr_north/`. Telegram is **@Npeppers_bot** only. This folder is protected business infrastructure; see [`PROTECTED_AGENTS.md`](../PROTECTED_AGENTS.md).

| This package | Not this package |
| --- | --- |
| TrueHold Wellness inbox / orders | Realtor property acquisition |
| **@Npeppers_bot** | **@PirateEye_bot** |
| `WELLNESS_ALERT_WEBHOOK_URL` | `ALERT_WEBHOOK_URL` (Mr North) |

## Workflow (as before)

Every alert includes the full business-inbox snapshot:

```
orders, payments, fulfillment, shipping, cancellations, peptides, other_actionable
```

```bash
cd truehold-wellness
python -m pip install -e ".[dev]"
python -m wellness_agent compose
python -m wellness_agent compose --type order --detail "New TrueHold Wellness order received."
python -m wellness_agent send --dry-run --type order
python -m pytest
```

`send` POSTs JSON with `agent=truehold-wellness-agent` to `WELLNESS_ALERT_WEBHOOK_URL` (never Mr North’s `ALERT_WEBHOOK_URL`). If `TELEGRAM_MODE=live` and the token is `@Npeppers_bot`, the same message is also delivered on Telegram.

## Telegram (@Npeppers_bot)

Source: https://core.telegram.org/bots/api

Live mode calls `getMe` and refuses `@PirateEye_bot`.

1. BotFather `/mybots` must list **Npeppers_bot**. A congratulations token that returns `401 Unauthorized` cannot run.
2. `.env`: `TELEGRAM_MODE=live`, `TELEGRAM_BOT_TOKEN=…`, optional `WELLNESS_TELEGRAM_CHAT_ID`.
3. `python -m wellness_agent telegram-poll`
4. In Telegram: `/start`, `/inbox`, `/order <product and qty>`

## Isolation

- Separate folder, package (`wellness_agent`), webhook env, Telegram bot, tests, and CI job
- Crypto/Hormuz content is rejected
- Realtor MLS/matching code is not used
