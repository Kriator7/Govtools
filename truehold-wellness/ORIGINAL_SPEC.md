# TrueHold Wellness — original agent spec

Restored from the deleted Govtools Wellness duplicate and bound to the live Telegram replacement **@THWellness_bot**.

| Source | Location |
| --- | --- |
| Original package | commit `cf24ec1` (`truehold/wellness_agent`) |
| Why it left this repo | commit `17d9c76` (user: live Wellness was already working elsewhere; this repo is Mr North / crypto) |
| Cloud agent that wrote it | [bc-01a00bdb-3ee5-7e43-829f-f2e9b1f1b839](https://cursor.com/agents/bc-01a00bdb-3ee5-7e43-829f-f2e9b1f1b839) |
| Telegram identity now | **@THWellness_bot** (`t.me/THWellness_bot`) |
| Deleted predecessor | `@Npeppers_bot` — BotFather `/deletebot` cannot be undone ([Telegram Bot Features](https://core.telegram.org/bots/features)) |

This folder is the Wellness agent. Do not mix it with Mr North (`ALERT_WEBHOOK_URL`, Hormuz/crypto copy) or realtor-agent (`@PirateEye_bot`).

## Canonical business copy

Every alert includes a **complete** inbox snapshot so none of these are dropped:

- orders
- payments
- fulfillment requests
- shipping issues
- cancellations/refunds
- peptide messages
- other actionable business email

Default snapshot copy (also stored in `wellness_agent/data/current_inbox.json`):

> Business: No new TrueHold Wellness order, payment, fulfillment request, shipping issue, cancellation/refund, peptide message, or other actionable business email appeared in the connected inbox since the previous check. The only new messages were routine/news content.

Categories are fail-closed. A missing key or empty `detail` raises `ValueError`.

## CLI (identical to commit `cf24ec1`)

Console scripts: `truehold-wellness-agent` and `truehold-wellness`.

```bash
cd truehold-wellness
python -m pip install -e ".[dev]"
python -m wellness_agent compose
python -m wellness_agent compose --json
python -m wellness_agent compose --type order --detail "New TrueHold Wellness order received."
python -m wellness_agent send --dry-run --type business
WELLNESS_ALERT_WEBHOOK_URL=https://example.invalid/wellness python -m wellness_agent send --type order
python -m wellness_agent ingest-email
python -m pytest
```

`--type` choices: `business` (default), `order`, `payment`, `fulfillment`, `shipping`, `cancellation`, `peptide`, `manual`.

Default headlines: business inbox, order, payment, fulfillment request, shipping issue, cancellation/refund, peptide message, manual alert.

`send` POSTs JSON to **`WELLNESS_ALERT_WEBHOOK_URL` only**. It does not read Mr North’s `ALERT_WEBHOOK_URL`. User-Agent: `truehold-wellness-agent/0.1`. Timeout: 15s.

Payload `agent` / `source`: `truehold-wellness-agent`.

A `business` compose with no `--detail` prints the snapshot only (no `TrueHold Wellness alert —` prefix). Other types prepend:

```
TrueHold Wellness alert — {headline}

{detail}

---

{inbox snapshot}
```

## Telegram (@THWellness_bot)

The original `cf24ec1` agent had no Telegram. The later `@Npeppers_bot` layer added `/start`, `/inbox`, and `/order`. That inbound surface is preserved here on **@THWellness_bot**, plus live-shop inventory sheets (`/catalog`, `/product`).

`/start` links the operator chat. `/order` and `ingest-email` fire the original inbox reflexes so operators are notified of orders, payments, fulfillment, shipping, cancellations, peptides, and other actionable email. Every alert still includes the complete snapshot.

Bot API: https://core.telegram.org/bots/api

| Command | Behavior |
| --- | --- |
| `/start` `/help` | Link operator chat for order/email-reflex alerts |
| `/inbox` | Full business-inbox snapshot |
| `/catalog` `/product` | Locked inventory sheets |
| `/order <detail>` | Order trigger, operator notify, inventory PDF when SKU matches |
| `/schedule` | Team contact |

Live mode calls `getMe` and refuses `@PirateEye_bot` and the deleted `@Npeppers_bot` username.

```bash
python -m wellness_agent whoami
python -m wellness_agent configure-telegram
python -m wellness_agent telegram-poll
```

## Isolation vs crypto

Wellness must not include keys `catalyst`, `btc_threshold`, `capital_regime`, `macro_liquidity`, `geopolitical_catalyst`, or phrases such as Strait of Hormuz / BTC threshold. Crypto triggers raise `ValueError("TrueHold Wellness agent does not send crypto/macro triggers")`.

## What was never in the original duplicate

Live Gmail/IMAP polling was not shipped. The inbox is the JSON snapshot until a live mailbox connector is added **in this folder only**.
