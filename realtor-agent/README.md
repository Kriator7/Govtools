# Realtor Property Acquisition Automation

Self-contained automation platform for **one Nevada realtor**, **one authorized MLS/API connection**, and the realtor’s existing investor clientele.

Telegram for this folder is **@PirateEye_bot** only. TrueHold Wellness order emails use **@THWellness_bot** in `truehold-wellness/` — a different company, different files, different architecture. This folder is protected business infrastructure; see [`PROTECTED_AGENTS.md`](../PROTECTED_AGENTS.md).

This folder is the entire agent. Copy `realtor-agent/` to move the project. Nothing outside this directory is required to run, test, or deploy the service.

The system **never** autonomously executes a real-estate transaction, signs documents, or submits contractual paperwork. Realtor approval is required before investor notification and before any document leaves `DRAFT`.

## Workflow

```
MLS/API → ingest → normalize → match → score → Telegram review
  → approve/reject/snooze → investor notify → investor response
  → Transaction (spine) → document prep → realtor review
  → e-sign / transaction platform → closing tracking
```

Every meaningful action is tied to an opportunity ID and, after interest, a transaction ID such as `TX-2026-000123`.

## First milestone (local, mocks only)

No live MLS, Telegram, Twilio, or e-sign credentials are required.

```
Sample Investor CSV
  → investor + criteria records
  → mock MLS listings
  → deterministic matching
  → opportunity
  → Telegram realtor alert (written to data/exports/)
  → approve
  → mock investor SMS
  → investor YES
  → transaction record
  → sample PDF populated
  → audit + timeline
```

```bash
cd realtor-agent
python -m pip install -e ".[dev]"
cp .env.example .env
python -m app.cli demo
python -m pytest
```

Testing uses the confirmed CardanoMint operator mailbox `cardanomint@gmail.com` as the email from-address and relay inbox (`EMAIL_FROM`, `EMAIL_RELAY_TO`). Damian’s live preference is SMS; test SMS is relayed to `SMS_RELAY_TO` when set. Set `EMAIL_RELAY_MODE=false` / `SMS_RELAY_MODE=false` later when mail and texts should go to real recipients. Zillow emails in that inbox are not an MLS source.

Watch `jrupe7@gmail.com` for Damian packet replies: `python -m app.cli inbox-poll`. That mailbox needs its own Gmail App Password (`IMAP_PASSWORD`). Without it, polling falls back to CardanoMint IMAP and still only applies Damian / Home Finder mail. The Pirates IG LLC Numbers sheets are test templates only; Damian’s live row is created when Packet 1 arrives.

API (after `uvicorn app.main:app --reload --app-dir .` from this folder):

- `GET /health`
- `GET /health/database`
- `GET /health/mls`
- `GET /health/telegram`
- `GET /health/twilio`
- `GET /health/email`

## Stack

| Layer | Choice | Docs |
| --- | --- | --- |
| API | Python 3.12+, FastAPI, Pydantic | https://fastapi.tiangolo.com/ |
| ORM | SQLAlchemy 2.0 | https://docs.sqlalchemy.org/en/20/ |
| Migrations | Alembic | https://alembic.sqlalchemy.org/en/latest/ |
| Local DB | SQLite via `DATABASE_URL` | — |
| Production DB | PostgreSQL / Cloud SQL | https://cloud.google.com/sql/docs/postgres |
| Queue | Celery + Redis (optional locally) | https://docs.celeryq.dev/en/stable/ |
| Runtime | Cloud Run | https://cloud.google.com/run/docs |
| Secrets | env locally; Secret Manager in GCP | https://cloud.google.com/secret-manager/docs |
| Documents | local disk or Cloud Storage | https://cloud.google.com/storage/docs |
| Realtor alerts | Telegram Bot API (mock or live) | https://core.telegram.org/bots/api |
| Operator email | Gmail SMTP + App Password | https://developers.google.com/workspace/gmail/imap/imap-smtp |
| Investor SMS | Twilio Messages (mock or live) | https://www.twilio.com/docs/sms |

Live vendor adapters are interfaces plus mocks first. Do not invent MLS vendor schemas. Plug in an authorized feed when the realtor supplies access.

## Architecture

The **transaction is the spine**.

- Listings create **opportunities** when they match an active criteria profile at or above `ALERT_MIN_SCORE` (default 70).
- Opportunities connect one property to one investor profile.
- Realtor approval is required before investor notification (`APPROVED_FOR_INVESTOR_NOTIFICATION`).
- Investor `YES` creates a **Transaction**. Communications, documents, signatures, and timeline events attach to it.
- Rejection reasons are stored for later matching intelligence. Criteria are **never** auto-changed from AI or rejection inference.

Deterministic rules own price, ZIP, beds, exclusions, and other thresholds. AI may summarize, explain, and draft — it must not sign, invent contract values, change price, waive contingencies, or impersonate the realtor.

## Data model (realtor-scoped)

Every major table includes `realtor_id` so additional realtors can be added later without a rewrite. There is no multi-user dashboard in this MVP.

Credentials are **not** stored in PostgreSQL. Use `mls_config_ref` / Secret Manager names only.

## Matching and scoring

- Strict miss → no opportunity.
- Preferred miss → still matches; score drops; shown as a potential issue.
- Categories: 90–100 excellent, 80–89 strong, 70–79 possible, below 70 stored only if `ALERT_BELOW_THRESHOLD=true`.
- Weights: `mappings/scoring_weights.json`.
- Re-alert only on material changes (price, status, seller financing, occupancy, and related fields).

## Documents and Nevada forms

`templates/documents/purchase_agreement/v1/` is a **placeholder**, not a legal form.

Do not assume rights to store, populate, transmit, or e-sign Nevada REALTORS®, MLS, brokerage, or transaction-platform forms. Confirm those rights before production. If the realtor already uses a transaction platform, prefer an approved API over recreating proprietary workflows.

Draft documents always require realtor review:

`DRAFT → READY_FOR_REVIEW → APPROVED_BY_REALTOR → SENT_FOR_SIGNATURE → SIGNED → EXECUTED`

Executed files are never overwritten.

## Configuration

Copy `.env.example` to `.env`. Defaults use mock providers and SQLite at `data/realtor_agent.db`.

Production:

1. `DATABASE_URL=postgresql+psycopg://...` (Cloud SQL)
2. `SECRET_BACKEND=gcp` and Secret Manager names for MLS, Telegram, Twilio, AI, e-sign
3. `STORAGE_BACKEND=gcs`
4. `TELEGRAM_MODE=live` / `EMAIL_PROVIDER=smtp` / `SMS_PROVIDER=twilio` only after credentials exist. Keep `EMAIL_RELAY_MODE=true` and `SMS_RELAY_MODE=true` until testing is confirmed.
5. Cloud Scheduler → `POST /api/v1/jobs/ingest-listings` and `POST /api/v1/jobs/match-listings`

## Docker

```bash
cd realtor-agent
docker compose up --build
```

## Tests

```bash
cd realtor-agent
python -m pytest
```

Covers criteria, matching, scoring, exclusions, duplicates, transaction states, document field mapping, mock MLS/Telegram/Twilio, database ingest, document generation, and the end-to-end mock workflow.

## Incremental phases

| Phase | Status in this folder |
| --- | --- |
| 1 Foundation | Done — FastAPI, models, CRUD, audit |
| 2 Investor import | Done — CSV/Excel |
| 3 MLS integration | Mock provider + interface |
| 4 Matching engine | Done — deterministic |
| 5 Telegram agent | Live adapter + `/start` link + `telegram-poll` for phone buttons |
| 6 Investor comms | Live Gmail SMTP + SMS/Twilio adapters; relays stay on during testing |
| 7 Transaction engine | Done — explicit state machine |
| 8 Document engine | Done — placeholder PDF + field map |
| 9 Signature / platform | Interface + mock only |
| 10 Analytics | Event table + `/api/v1/analytics/summary` stub |

Replace mock integrations one at a time after this local workflow is stable.

## Live email (CardanoMint Gmail)

Do not put the Gmail password in git. Use a 16-character App Password, not the account password.

Sources:

- App passwords: https://support.google.com/accounts/answer/185833
- Gmail SMTP: https://developers.google.com/workspace/gmail/imap/imap-smtp
- Device/app SMTP: https://support.google.com/a/answer/176600

1. Turn on 2-Step Verification for `cardanomint@gmail.com`.
2. Open https://myaccount.google.com/apppasswords and create an app password named `realtor-agent`.
3. Copy `.env.example` to `.env` and set:

```
EMAIL_PROVIDER=smtp
EMAIL_FROM=cardanomint@gmail.com
EMAIL_RELAY_TO=cardanomint@gmail.com
EMAIL_RELAY_MODE=true
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=cardanomint@gmail.com
EMAIL_SMTP_PASSWORD=xxxxxxxxxxxxxxxx
EMAIL_SMTP_STARTTLS=true
```

4. Send a ping: `python -m app.cli send-test-email`
5. Confirm the message in the CardanoMint inbox. Relay mode keeps intended investor addresses in the body and `X-Intended-Recipient` header.

## Damian packet inbox (IMAP)

Source: https://developers.google.com/workspace/gmail/imap/imap-smtp  
App passwords: https://support.google.com/accounts/answer/185833

Watch `jrupe7@gmail.com` for Damian Einbinder replies (`binder@thehomefinderlv.com`) to [`REALTOR_DOCUMENT_CHECKLIST.md`](REALTOR_DOCUMENT_CHECKLIST.md). When a matching email arrives, `inbox-poll` writes the fields onto Damian’s realtor / investor records.

1. Create a Gmail App Password on **`jrupe7@gmail.com`** (this is not the CardanoMint SMTP password).
2. Set:

```
IMAP_USERNAME=jrupe7@gmail.com
IMAP_PASSWORD=xxxxxxxxxxxxxxxx
IMAP_WATCH_ADDRESS=jrupe7@gmail.com
```

3. Poll: `python -m app.cli inbox-poll --once` then `python -m app.cli inbox-poll`
4. Raw mail is stored under gitignored `data/inbox/`. Packet status is `data/packets/STATUS.md`.
5. Relays stay on. MLS website passwords, Twilio tokens, and e-sign passwords in the email body are redacted and not stored.

If `IMAP_PASSWORD` is missing, the same command still polls `cardanomint@gmail.com` with the SMTP App Password and applies Damian mail that lands there (for example a CC or forward).

## Live Telegram (operator + Damian group)

Source: https://core.telegram.org/bots/api

Realtor acquisition uses **@PirateEye_bot** only. Never put `@THWellness_bot` or `@Mr_North_bot` in this folder.

1. Add `@PirateEye_bot` to the operator/Damian group (currently **MaximumMint & Agent Real**). Privacy mode can stay on; Approve/Reject buttons still work because they are on the bot’s own cards.
2. Get the group id the same way as North (`ID Bot` → **My Group**). It is a negative number. Do **not** use the Mr North BLS group (`-1003939359929`).
3. Put the token and group id in `.env`:

```
TELEGRAM_MODE=live
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_OPERATOR_CHAT_ID=-5372586958
```

4. Confirm identity: `python -m app.cli telegram-whoami` must print `PirateEye_bot`.
5. Start polling on the machine that should receive button taps: `python -m app.cli telegram-poll`
6. Intro ping: `python -m app.cli telegram-hello`
7. Mock listing cards: `python -m app.cli alert` (use `python -m app.cli alert --resend-pending --limit 2` if listings already matched)
8. Damian or the operator taps APPROVE / REJECT / SNOOZE in the group. APPROVE notifies the **test** investor channel (SMS relay + email copy). Relays stay on. Do not text Damian or live investors.
9. Damian can reply in the group to correct the buy box (`300k min`, `$600,000 max`, buy-and-hold). PirateEye applies that to the investor on the last DETAILS card. For group text to arrive, reply to a PirateEye card or disable BotFather privacy for `@PirateEye_bot`.
10. Pasted note: `python -m app.cli telegram-apply-note --text-file note.txt --send`

If Damian is added to the group, PirateEye records `@damianlasvegas` on the Damian realtor row and keeps Test Operator as the matcher/alert sender. Packet 1 still does not overwrite Test Operator.

`/start` in a private chat still links Test Operator. In the group, `/start@PirateEye_bot` (or the env chat id) is enough because Bot API privacy may hide ordinary group text.

Polling uses `getUpdates` and calls `deleteWebhook` first. Use the HTTPS webhook (`POST /api/v1/webhooks/telegram`) later if this process has a public URL and `TELEGRAM_WEBHOOK_SECRET`.

## Investor SMS (Damian’s preference, still testing)

Damian asked for investor contact by text. The test investor template now prefers SMS. Live Twilio still must not text Damian, Amos, or real investors.

1. Keep `SMS_RELAY_MODE=true`.
2. Set `SMS_RELAY_TO` to **your** mobile number in E.164 (`+1…`).
3. Leave `SMS_PROVIDER=mock` until Twilio is ready. Mock writes `data/exports/sms_outbox.json`.
4. When Twilio credentials exist, set `SMS_PROVIDER=twilio` plus `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`. Trial accounts can only text verified numbers: https://www.twilio.com/docs/sms
5. Ping: `python -m app.cli send-test-sms`
6. `NOTIFY_EMAIL_COPY=true` also puts a copy in `cardanomint@gmail.com` so you can see the investor notice without a phone.

Do not set `SMS_RELAY_MODE=false` until testing is confirmed and each investor has SMS permission.
