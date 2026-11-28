# Nod (self-hosted only)

Nod is n8n's personal assistant: one chat, a private Linux workspace, and a
browser. Official intro: [What is Nod](https://nod.n8n.io/docs/get-started/what-is-nod/).

It is **not** the n8n AI Assistant, and it is **not** a fourth Telegram business
bot. Official FAQ: [Do I need n8n?](https://github.com/n8n-io/nod/blob/4178ac0f7e712dd3c1e392e0161aec81af8beb64/README.md).

This folder is a **house overlay**. The application lives in a pinned clone of
[`n8n-io/nod`](https://github.com/n8n-io/nod) on the Mac. Govtools does not
vendor Nod, does not store its Vault key, and does not run it on Cursor cloud
VMs.

Pinned revision: `4178ac0f7e712dd3c1e392e0161aec81af8beb64` (2026-11-27). See
[`UPSTREAM.json`](UPSTREAM.json).

## House decision

| Choice | Value | Why |
| --- | --- | --- |
| Host | James's Mac, Docker Desktop | [Host on a Mac mini](https://nod.n8n.io/docs/deploy/mac-mini/) |
| Bind | `127.0.0.1:4310` | Official default in [`.env.example`](https://github.com/n8n-io/nod/blob/4178ac0f7e712dd3c1e392e0161aec81af8beb64/deployment/self-host/.env.example) |
| Remote access | SSH tunnel only | [Open a remote server without a domain](https://nod.n8n.io/docs/deploy/self-host/) |
| Model | House Ollama | [Local models](https://nod.n8n.io/docs/connect/local-models/) |
| Telegram | New bot, in-app Channels | Never reuse `@Mr_North_bot`, `@THWellness_bot`, or `@PirateEye_bot` |
| Apps / Composio | Skip until approved | Default proxy is n8n-hosted `https://composio.n8n.cloud` |
| Analytics / feedback | Off | [Configuration reference](https://nod.n8n.io/docs/deploy/configuration/) |

Rejected: n8n managed hosting, public HTTPS on 80/443, Tailscale Funnel, this
Cursor cloud VM, Railway, boxd, and any reuse of protected business bot tokens.

## What you need

From [Host your own server](https://nod.n8n.io/docs/deploy/self-host/):

1. Docker Engine 25+ with Compose v2, OpenSSL, and `shasum`.
2. Two CPU cores, 8 GB Docker memory, 50 GB disk as a starting point.
3. A model **after** startup. No provider key is required to install.

House extras:

1. Keep ports **5000**, **15678** (n8n), **15679** (bridge), **11434** (Ollama),
   **3848** (HUD), **8010/8011** (Colibri), **5432/6379/8080** (realtor-agent
   local stack) unused by Nod.
2. Ollama must serve a **tool-calling** model with **at least 65,536** context.
   Official example: `OLLAMA_CONTEXT_LENGTH=65536 ollama serve` then
   `ollama pull` a Tools model ([Local models](https://nod.n8n.io/docs/connect/local-models/)).
3. Do **not** start the stack until James says **yes**. `setup.sh` writes
   `NOD_AUTH_TOKEN`, `NOD_VAULT_KEY`, and `NOD_POSTGRES_PASSWORD` into a private
   `.env`. Do not print those values.

## Install on the Mac (source stack)

Commands below are from [Host your own server](https://nod.n8n.io/docs/deploy/self-host/)
and [`setup.sh`](https://github.com/n8n-io/nod/blob/4178ac0f7e712dd3c1e392e0161aec81af8beb64/deployment/self-host/setup.sh).

1. Clone the pinned revision into a dedicated folder. Do not clone into this
   Govtools working tree.

```bash
mkdir -p "$HOME/openhands-local/var/nod"
git clone https://github.com/n8n-io/nod.git "$HOME/openhands-local/var/nod/source"
cd "$HOME/openhands-local/var/nod/source"
git checkout 4178ac0f7e712dd3c1e392e0161aec81af8beb64
cd deployment/self-host
```

2. Generate keys. This creates `.env` and does not print secrets.

```bash
unset NOD_AUTH_TOKEN NOD_VAULT_KEY NOD_POSTGRES_PASSWORD
sh setup.sh
```

3. Merge the house overlay. It never replaces the three secrets or
   `COMPOSE_PROJECT_NAME`.

```bash
python3 /path/to/Govtools/scripts/check_nod_house.py apply \
  --env "$HOME/openhands-local/var/nod/source/deployment/self-host/.env"
```

4. Stop. Show James `docker compose --file compose.yaml --env-file .env config`
   output. Start only after an explicit **yes**:

```bash
docker compose --file compose.yaml --env-file .env up -d --build --wait
```

5. Open `http://localhost:4310` on the Mac and paste `NOD_AUTH_TOKEN` from
   `.env`. Finish onboarding with the OpenAI-compatible / Ollama connection.
   Official: [Connect Nod](https://nod.n8n.io/docs/connect/local-models/).

6. From another device, keep loopback + an SSH tunnel. Do not enable the
   Compose `https` profile.

```bash
ssh -L 4310:127.0.0.1:4310 james@the-mac
```

Source: [Open a remote server without a domain](https://nod.n8n.io/docs/deploy/self-host/).

## Telegram

Leave every `TELEGRAM_*` variable blank so Channels stays app-managed.
Official: [Telegram and WhatsApp](https://nod.n8n.io/docs/use/channels/).

Create a **new** BotFather bot. Polling needs outbound internet only. Do not
point Nod at `@Mr_North_bot`, `@THWellness_bot`, or `@PirateEye_bot`.

## Backup

Before any update, from the compose directory, using
[Back up and update a server](https://nod.n8n.io/docs/deploy/server-operations/):

```bash
mkdir -p "$HOME/openhands-local/var/nod/backups"
sh backup.sh "$HOME/openhands-local/var/nod/backups/nod-backup-$(date +%F)"
```

The backup includes `.env` (token, Vault key, database password). Store it
encrypted. A Postgres dump without the Vault key cannot recover saved
credentials.

Copying this Govtools folder is **not** a Nod backup.

## Policy checker

```bash
python scripts/check_nod_house.py
python scripts/check_nod_house.py --env /path/to/nod/deployment/self-host/.env
```

CI runs the first form. It refuses cloud binds, reserved house ports, Funnel,
Composio cloud URLs in the overlay, and protected bot names.
