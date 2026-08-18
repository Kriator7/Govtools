# TrueHold Wellness — business inbox + @THWellness_bot

Self-contained **TrueHold Wellness** agent restored from the original inbox-snapshot design (orders, payments, fulfillment, shipping, cancellations, peptides). Copy `truehold-wellness/` to move it.

Full original spec: [`ORIGINAL_SPEC.md`](ORIGINAL_SPEC.md) (from commit `cf24ec1` / cloud agent that first wrote Wellness in this repo).

It does **not** import `realtor-agent/` or `mr_north/`. Telegram is **@THWellness_bot** only (`t.me/THWellness_bot`). `@Npeppers_bot` was deleted in BotFather and cannot be undeleted ([Telegram `/deletebot`](https://core.telegram.org/bots/features)). This folder is protected business infrastructure; see [`PROTECTED_AGENTS.md`](../PROTECTED_AGENTS.md).

| This package | Not this package |
| --- | --- |
| TrueHold Wellness inbox / orders | Realtor property acquisition |
| **@THWellness_bot** | **@PirateEye_bot** |
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

`send` POSTs JSON with `agent=truehold-wellness-agent` to `WELLNESS_ALERT_WEBHOOK_URL` (never Mr North’s `ALERT_WEBHOOK_URL`). If `TELEGRAM_MODE=live` and the token is `@THWellness_bot`, the same message is also delivered on Telegram.

## Telegram (@THWellness_bot)

Source: https://core.telegram.org/bots/api

Live mode calls `getMe` and refuses `@PirateEye_bot` and the deleted `@Npeppers_bot`.

1. BotFather `/mybots` must list **THWellness_bot**.
2. `.env`: `TELEGRAM_MODE=live`, `TELEGRAM_BOT_TOKEN=…`, optional `WELLNESS_TELEGRAM_CHAT_ID`.
3. `python -m wellness_agent whoami` — must return `THWellness_bot`.
4. `python -m wellness_agent configure-telegram` — name, about, `/start` `/inbox` `/order` `/help`.
5. `python -m wellness_agent telegram-poll`
6. In Telegram: `/start`, `/inbox`, `/catalog`, `/product klow`, `/order <product and qty>`

## Inventory (locked information sheets)

Live shop SKUs from https://trueholdwellness.com/sitemap.ols.xml. Existing Tirzepatide, NAD+, Semax, and Retatrutide PDFs are stored as-is. KLOW, MOTS-c, SS-31, and GHK-Cu use the same locked-sheet layout.

```bash
python -m wellness_agent catalog
python -m wellness_agent product klow
```

Telegram: `/catalog` and `/product <name>` send the PDF. New sheets are educational only — they do not invent reconstitution or dosing. Protocol details stay case-by-case (`/schedule`).

Rebuild missing generated sheets:

```bash
python -m pip install -e ".[dev]"
python -m wellness_agent.inventory.build_pdfs
```

## Isolation

- Separate folder, package (`wellness_agent`), webhook env, Telegram bot, tests, and CI job
- Crypto/Hormuz content is rejected
- Realtor MLS/matching code is not used
