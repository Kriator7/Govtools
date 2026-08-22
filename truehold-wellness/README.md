# TrueHold Wellness — orders, inventory, and client tracking

Telegram: **@THWellness_bot** only (`t.me/THWellness_bot`).

This folder is the entire agent. Copy `truehold-wellness/` to run it in its own Docker container. Nothing outside this directory is required.

Full spec: [`ORIGINAL_SPEC.md`](ORIGINAL_SPEC.md). `@Npeppers_bot` was deleted in BotFather and cannot be undeleted ([Telegram `/deletebot`](https://core.telegram.org/bots/features)). Live `getMe` must return `THWellness_bot`.

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

`send` POSTs JSON with `agent=truehold-wellness-agent` to `WELLNESS_ALERT_WEBHOOK_URL`. If `TELEGRAM_MODE=live` and staff is allowlisted, the same message is delivered on **@THWellness_bot**.

Customer `/order` and the picture-menu confirm still use the original protocol for **staff**: full inbox snapshot (orders, payments, fulfillment, shipping, cancellations, peptides, other_actionable). The customer only sees a short confirmation — never the staff inbox.

Email reflexes:

```bash
python -m wellness_agent ingest-email
python -m thw ingest
```

## Telegram (@THWellness_bot)

Source: https://core.telegram.org/bots/api

Live mode calls `getMe` and refuses any username that is not `THWellness_bot`.

### Customer picture menu

1. `/start` (or a first hello) sends the official TrueHold Wellness logo with a warm welcome and a short explainer of how ordering works, plus the **quick menu** (names only). It does not ask for a phone yet.
2. Hello, hey, or good morning after that is a short “hi again” — the intro plays once per session.
3. Tap one name — we send **that tile**, not every SKU photo. Quantity and phone steps also send a navy/gold molecule banner.
4. **Order this** → 1 / 2 / 3 dry vials → **Yes — Las Vegas resident**.
5. **View PDF in Telegram** sends the information sheet as a PDF in the chat (tap to view or download). It does not open the product webpage.
6. Local Las Vegas: **Zelle is best** (details on the confirmation call). Debit card instead of Zelle: **Pay by debit card on the site**.
7. Phone is asked only after an order (or `/schedule`). Telegram cannot expose a phone unless the client shares it (**Share my phone number** or type it) so the team can call to confirm, consult, and complete required documentation.
8. A confirmed interest order **decrements on-hand inventory** (when Inventory.on_hand is set) and appends a row to the working `trueholdwellness-orders.xlsx` ledger, same as the old agent.
9. **Prep and local delivery are for Las Vegas residents only.** Shipping is **dry (lyophilized) vials only** — not reconstituted product.
10. Staff are notified with the number (or a note that it is missing) plus the inventory adjustment. The customer gets a short confirmation plus the PDF in Telegram.

Public BotFather commands are only `/start` `/menu` `/schedule` `/help`. `/inbox` is not in the customer menu.

### Staff access (fail-closed)

No Telegram command can grant admin. `/start`, `/staff`, `/admin`, and `/operator` never promote a customer.

Staff IDs are set only in `truehold-wellness/.env` on the machine that runs the bot:

1. Set `WELLNESS_OPERATOR_USER_IDS` to the staff Telegram user id(s) (private chat id is the same number), **or**
2. Set `WELLNESS_TELEGRAM_CHAT_ID` to that same private chat id.

`/inbox` runs only in a **private** 1:1 chat with an allowlisted `from.id`. Group chats are denied so the snapshot cannot leak to other members. A leftover `data/operator.json` is ignored.

Wrong or missing staff identity replies `That command is for TrueHold staff only.`

### Run locally

1. BotFather `/mybots` must list **THWellness_bot**.
2. `.env`: `TELEGRAM_MODE=live`, `TELEGRAM_BOT_TOKEN=…`, plus a staff allowlist as above.
3. `python -m wellness_agent whoami` — must return `THWellness_bot`.
4. `python -m wellness_agent configure-telegram` — customer command menu by default; staff `/inbox` only on operator chats.
5. `python -m wellness_agent telegram-poll` — stays up: if getUpdates or the process dies, it restarts. `python -m wellness_agent telegram-status` shows whether the heartbeat is fresh. Production wrapper: `bash scripts/keep_telegram_poll.sh` (only one copy).
6. In Telegram as a customer: `/start` for the welcome, tap one name, order 1–3 vials, then share a phone if asked. `/schedule` shows `trueholdwellness@gmail.com` as a tappable email that opens the client’s mail app with our address filled in.
7. In Telegram as staff: `/inbox` and `/stock` after allowlisting.

Rebuild picture cards and brand graphics:

```bash
python -m wellness_agent.inventory.build_cards
python -m wellness_agent.inventory.build_brand
```

## Inventory (locked information sheets)

Live shop SKUs from https://trueholdwellness.com/sitemap.ols.xml.

| Live SKU | Vial in stock | Sheet |
| --- | --- | --- |
| All eight shop SKUs | mg on the label | Rebuilt by `python -m wellness_agent.inventory.build_pdfs` — molecule, data, risks, FDA, mix, 0.5 mL syringe |
| Logo at `inventory/assets/logo.jpeg` | | Orders workbook at `inventory/workbooks/trueholdwellness-orders.xlsx` |

The Deleted Account Telegram chat still holds Finder copies of the old files. They are **not** pulled automatically. To import them:

1. In Telegram, open the Deleted Account chat → **Files**.
2. **Show in Finder** and copy `trueholdwellness-orders.xlsx` plus the PDFs.
3. Paste into `truehold-wellness/data/imports/legacy/`.
4. Run:

```bash
python -m pip install -e ".[dev]"
python -m wellness_agent ingest-files
```

Matching PDFs overwrite `inventory/pdfs/`. The xlsx is stored as the live ledger (`data/imports/trueholdwellness-orders.xlsx`). Extra SKUs the old chat never had (KLOW, MOTS-c, SS-31, GHK-Cu) stay in place unless you drop those PDFs too.

```bash
python -m wellness_agent catalog
python -m wellness_agent stock
python -m wellness_agent product klow
python -m wellness_agent.inventory.build_pdfs
python -m wellness_agent.inventory.build_workbook
```

Telegram: `/menu` then **View PDF in Telegram** sends the sheet. Every PDF is written for the milligram vial in stock (molecule, testing data, risks, FDA status, reconstitution, and U-100 / 0.5 mL syringe marks). Mix math is checked in `wellness_agent/inventory/protocol.py` before a sheet is built. The bot still does not dose in chat.

```bash
python -m wellness_agent.inventory.build_pdfs
```

If `ingest-files` overwrites PDFs with Finder copies, rebuild with `build_pdfs` to restore the vial-specific sheets.

## Docker

Image: https://hub.docker.com/_/python  
Dockerfile reference: https://docs.docker.com/reference/dockerfile/  
Compose: https://docs.docker.com/compose/  
getUpdates: https://core.telegram.org/bots/api#getupdates

1. Copy `.env.example` to `.env` and set `TELEGRAM_MODE=live`, `TELEGRAM_BOT_TOKEN`, and staff ids.
2. From this folder: `docker compose up --build`
3. The container runs `python -u -m wellness_agent telegram-poll`. Only one getUpdates client may use this token.
