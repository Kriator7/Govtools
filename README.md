# Govtools

Three **independent** Telegram agents. They do not share bots, tokens, databases, documentation, or containers. Open the folder for the agent you want; run it from that folder only.

| Folder | Agent | Telegram | Container |
| --- | --- | --- | --- |
| [`truehold-wellness/`](truehold-wellness/) | TrueHold Wellness — orders, inventory, clients | `@THWellness_bot` | `docker compose up` in that folder |
| [`mr_north/`](mr_north/) | Agent North — market watcher | `@Mr_North_bot` | `docker compose up` in that folder |
| [`realtor-agent/`](realtor-agent/) | PirateEye — MLS matching (API key pending) | `@PirateEye_bot` | `docker compose up` in that folder |

Each folder has its own `README.md`, `.env.example`, `Dockerfile`, and `docker-compose.yml`. Do not copy one agent’s `.env` into another.

Repo policy (not product docs): [`PROTECTED_AGENTS.md`](PROTECTED_AGENTS.md).
