---
name: nod-self-host
description: >-
  Operate n8n Nod as a self-hosted personal assistant on James's Mac only.
  Use when the user mentions Nod, nod.n8n.io, or a self-hosted n8n assistant.
  Never deploy Nod to cloud VMs, n8n managed hosting, Railway, or Funnel.
---

# Nod — self-hosted only

Nod is n8n's personal assistant ([What is Nod](https://nod.n8n.io/docs/get-started/what-is-nod/)).
It is **not** the n8n AI Assistant and **not** `@Mr_North_bot` /
`@THWellness_bot` / `@PirateEye_bot`.

Canonical overlay: `nod/` in Govtools. Application source is a pinned clone of
https://github.com/n8n-io/nod on the Mac, not this repo.

## Hard rules

1. Self-hosted Docker stack only
   ([Host your own server](https://nod.n8n.io/docs/deploy/self-host/)).
2. Bind `127.0.0.1:4310`. Remote access is an SSH tunnel, never Tailscale Funnel
   and never the Compose `https` profile unless James explicitly asks.
3. Do not start the stack, rotate `NOD_AUTH_TOKEN`, or replace `NOD_VAULT_KEY`
   without an explicit **yes**.
4. Do not print `.env` secrets.
5. Do not run Nod as the house assistant on a Cursor cloud VM.
6. New Telegram bot only. Configure in the app with all `TELEGRAM_*` unset.
7. Skip Composio / Apps. Default proxy is `https://composio.n8n.cloud`.
8. Keep house n8n on `127.0.0.1:15678`. Nod does not replace it.

## Model

House Ollama is on the Mac. Inside Nod Docker, `localhost` is the container.
Use `http://host.docker.internal:11434/v1`
([Local models](https://nod.n8n.io/docs/connect/local-models/)).
Need a tool-calling model and `OLLAMA_CONTEXT_LENGTH=65536`.

## Commands

```bash
python scripts/check_nod_house.py
python scripts/check_nod_house.py apply --env "$HOME/openhands-local/var/nod/source/deployment/self-host/.env"
```

Install, backup, and tunnel steps: `nod/README.md`.
Pinned commit: `nod/UPSTREAM.json`.
