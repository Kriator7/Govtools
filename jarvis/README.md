# JARVIS Mark VII

Executive assistant for schedules, memory, and read-only operations. It does not replace the existing Ollama or voice processes, and it does not share code with Mr North, realtor-agent, or TrueHold Wellness.

Timezone for every schedule and tool result: `America/Los_Angeles`.

## What was discovered

1. House n8n is `http://127.0.0.1:15678` on the operator Mac (`n8nio/n8n:2.3.2`). From this cloud runtime that port does not answer, so its status is **DISCONNECTED**.
2. Ollama `http://127.0.0.1:11434` does not answer here. JARVIS only calls `/api/chat` when a host is configured. It does not pull a model.
3. No voice health URL is configured. The voice stack was not started or edited.
4. A lab n8n, PostgreSQL 16, and Qdrant were started on loopback so the schedule contract could be tested. Lab n8n is `http://127.0.0.1:15680`. It is not the house instance.

## Layout

| Piece | Role |
| --- | --- |
| `python -m jarvis serve` | Operator UI on `http://127.0.0.1:8787` |
| `POST /mcp` | MCP JSON-RPC. Requires `Authorization: Bearer` from the credential file |
| `POST /api/internal/run` | n8n callback. Same bearer token. Not for the model to invent |
| PostgreSQL | Tasks, executions, memories, approvals, notifications |
| Qdrant | Collections `personal`, `business`, `confidential` |
| n8n | Scheduler. Initial automations are imported inactive |

Credentials live in `~/.config/jarvis/credentials.env` (`chmod 600`). See `.env.example`. Tool results redact those values. External mail and web pages are returned as `trust: untrusted` and are not executed.

## Connect

1. Confirm which n8n you are talking to. House: port `15678`. Lab compose in this folder uses port `15680`.
2. Put `POSTGRES_PASSWORD`, `N8N_API_KEY`, and `JARVIS_GATEWAY_TOKEN` in the credential file. Create the n8n key from **Settings → n8n API** ([authentication](https://docs.n8n.io/api/authentication/)). On n8n 2.3 the REST create call also needs `scopes` and `expiresAt`.
3. `python -m jarvis ensure-qdrant` creates the three collections ([Qdrant collections](https://qdrant.tech/documentation/concepts/collections/)).
4. `python -m jarvis status` prints a live probe. Trust that output, not this README, for connection state.
5. `PYTHONPATH=. python3 scripts/prove_n8n_schedule.py` activates a one-minute harmless workflow, waits for one `success` execution in `mode: trigger`, deletes that test workflow, and imports the six automations inactive.

Public API used for workflows: [create workflow](https://docs.n8n.io/connect/n8n-api/build-and-run/workflows). There is no public execute-by-id on this n8n, so the proof is a real schedule trigger.

## Initial automations

All six stay disabled until an operator approval exists **and** every required probe is `CONNECTED`. A notification is `CONNECTED` only after a webhook returns HTTP 2xx.

| Name | Cron (Pacific) | Tool | Also requires |
| --- | --- | --- | --- |
| TrueHold Daily Intelligence | `30 7 * * *` | `generate_morning_intelligence` | verified notification |
| Unified Action Alerts | `*/15 * * * *` | `monitor_priority_email` | email |
| AMINT Infrastructure Monitoring | `*/5 * * * *` | `check_node_health` | Cardano health URL |
| Daily Calendar Briefing | `0 7 * * *` | `get_daily_schedule` | calendar |
| Wellness Operations Review | `0 8 * * *` | `generate_business_report` | client ledger |
| Evening Task Reconciliation | `30 18 * * *` | `list_tasks` | verified notification |

An unreachable Cardano probe sets `actionable_failure` to false. It is not paged as a node failure. KES, VRF, and cold keys are never opened. Pool statistics stay unread until `CARDANO_NETWORK` is `preview` or `preprod`.

Invoice amounts are not calculated here. Use the TrueHold invoice application on the operator machine.

## Market and macro sources

- Prices: CoinGecko keyless `simple/price` ([docs](https://docs.coingecko.com/docs/keyless-public-api)). Midnight id `midnight-3` ([coin page](https://www.coingecko.com/en/coins/midnight-3)).
- Macro: BLS public API v1 ([signature](https://www.bls.gov/developers/api_signature.htm)). `mr_north/data/current_catalyst.json` is labeled `live: false`.
- Node releases: `https://api.github.com/repos/IntersectMBO/cardano-node/releases/latest`.

## Tests

```bash
cd jarvis
python -m pip install -e ".[dev]"
python -m pytest
```

PostgreSQL is required for `jarvis serve`. Unit tests set `JARVIS_STORE=memory` only inside the test process. The server refuses to pretend memory is PostgreSQL.
