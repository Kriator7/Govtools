# Govtools

This repository contains two independent, self-contained Python agents. They do not import from each other.

- `mr_north/` (package `mr_north`) — **Mr North**, a stdlib-only CLI that composes/sends crypto/macro alerts with a catalyst briefing. Tests live in the top-level `tests/`. Configured by the root `pyproject.toml`.
- `realtor-agent/` — a FastAPI + SQLAlchemy service (package `app`) for realtor property-acquisition automation. Self-contained: its own `pyproject.toml`, `tests/`, `Dockerfile`, and `docker-compose.yml`.

Standard commands are documented in `README.md` and `realtor-agent/README.md`; the CI matrix is in `.github/workflows/test.yml`. Prefer those as the source of truth for lint/test/build/run commands.

## Cursor Cloud specific instructions

- Python 3.12 is the interpreter. Both projects install as editable packages via the startup update script (`pip install -e ".[dev]"` at the root, then `pip install -e "./realtor-agent[dev]"`). No system services (Postgres/Redis) are required for local dev — the realtor-agent defaults to SQLite (`data/realtor_agent.db`) and mock MLS/Telegram/Twilio/e-sign/AI providers.
- `python` is not on PATH; use `python3`. Console scripts (`mr-north`, `realtor-agent`, `uvicorn`, `pytest`, `alembic`) install to `~/.local/bin`, which is not on PATH — invoke via module form instead, e.g. `python3 -m pytest`, `python3 -m mr_north ...`, `python3 -m uvicorn ...`.
- Run each project's tests from its own directory (`cd` first) so pytest picks up the right `pyproject.toml` and `testpaths`: root `python3 -m pytest` covers Mr North; `cd realtor-agent && python3 -m pytest` covers the realtor agent.
- Mr North is offline-only: `python3 -m mr_north compose` prints the alert; `send --dry-run` builds the payload without POSTing. A real `send` only POSTs when `ALERT_WEBHOOK_URL` (or `--webhook-url`) is set.
- Realtor-agent runs without a `.env` (config defaults already match `.env.example`: SQLite + all mock providers). The `.env` file is gitignored. `python3 -m app.cli demo` runs the full mock workflow (ingest → match → alert → approve → notify → transaction → PDF draft) and seeds a test operator realtor.
- Start the API from inside `realtor-agent/` with `python3 -m uvicorn app.main:app --reload --app-dir . --port 8080`. Tables auto-create on startup (`AUTO_CREATE_TABLES=true`). Health probes: `/health`, `/health/database`, `/health/mls`, `/health/telegram`, `/health/twilio`. Interactive docs at `/docs`.
- The realtor-agent `docker-compose.yml` (Postgres + Redis + Celery worker) is optional and only needed to exercise Postgres/Celery paths; it is not required for tests or the local demo.
