# Agent notes

This repository is **three independent products**. They do not share Telegram
bots, databases, application code, or domain language.

| Product | Folder | Telegram |
| --- | --- | --- |
| Mr North | `mr_north/` | @Mr_North_bot |
| Realtor acquisition | `realtor-agent/` | @PirateEye_bot |
| TrueHold Wellness | `truehold-wellness/` | @THWellness_bot |

Read `GLOSSARY.md` and `GLOSSARY-MAP.md` before naming things. Protected
agents cannot be deleted without two human confirmations (`PROTECTED_AGENTS.md`).

## Grill with Docs

When the user types `/grill-with-docs`, or asks to grill, interview, or
document a fuzzy plan **before implementation**, follow
`.agents/skills/grill-with-docs/SKILL.md`.

1. Read the matching glossary and the code. Look up facts; do not ask them.
2. Ask **one** decision per turn, with a recommended answer. Stop and wait.
3. Write settled terms into that context's `GLOSSARY.md` immediately.
4. Write an ADR only when the decision is hard to reverse, surprising without
   context, and a real trade-off.
5. Do not implement until the user confirms a shared understanding.

Helpers: `python scripts/grill_docs.py map|resolve|check|upsert-term|write-adr`.

## Local hardware and WD_BLACK

Durable work lives on the Mac with WD_BLACK mounted, not on a Cursor Cloud
VM. The working copy of this repo is
`/Volumes/WD_BLACK/Agent databank/projects/Govtools` (sandbox:
`/opt/agent-databank/projects/Govtools`). Check the databank with
`python3 /opt/oh-tools/agent_databank.py --check` before writing. If the
check fails, stop. Do not copy Govtools onto this Cloud VM disk and call
that the working copy.
