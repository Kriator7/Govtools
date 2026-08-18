# Realtor Property Acquisition Automation

Self-contained automation platform for **one Nevada realtor**, **one authorized MLS/API connection**, and the realtor’s existing investor clientele.

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

Testing uses the confirmed CardanoMint operator mailbox `cardanomint@gmail.com` as the email from-address and relay inbox (`EMAIL_FROM`, `EMAIL_RELAY_TO`). Set `EMAIL_RELAY_MODE=false` later when mail should go to real recipients. Zillow emails in that inbox are not an MLS source. The Pirates IG LLC Numbers sheets are test templates only; Damian is not loaded until testing is confirmed.

API (after `uvicorn app.main:app --reload --app-dir .` from this folder):

- `GET /health`
- `GET /health/database`
- `GET /health/mls`
- `GET /health/telegram`
- `GET /health/twilio`

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
4. `TELEGRAM_MODE=live` / `SMS_PROVIDER=twilio` only after credentials exist
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
| 5 Telegram agent | Mock + live adapter + approve/reject/snooze |
| 6 Investor comms | Mock SMS + Twilio adapter |
| 7 Transaction engine | Done — explicit state machine |
| 8 Document engine | Done — placeholder PDF + field map |
| 9 Signature / platform | Interface + mock only |
| 10 Analytics | Event table + `/api/v1/analytics/summary` stub |

Replace mock integrations one at a time after this local workflow is stable.
