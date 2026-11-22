# Govtools repo

Root context for rules that apply to the whole repository, not to a single
product. Product terms belong in that product's `GLOSSARY.md`.

## Language

**Protected agent**:
A production business agent in this repo that CI will refuse to delete unless two different people fill `.github/DELETE_AGENT_CONFIRMATION.json`.
_Avoid_: service, bot folder, package
_Alias_: protected-agents.json

**Grill with Docs**:
A design interview run before implementation: the agent reads this repo, asks one decision at a time, and writes settled terms and hard trade-offs into glossaries and ADRs.
_Avoid_: brainstorm, planning chat
_Alias_: grill-with-docs

**Mr North**:
The TrueHold crypto-alerts product. Telegram identity is @Mr_North_bot. Not Wellness. Not realtor.
_Avoid_: North bot, crypto agent when those names are used for Wellness or realtor work

**Realtor acquisition**:
The Nevada realtor matching product. Telegram identity is @PirateEye_bot.
_Avoid_: PirateEye when naming the product folder

**TrueHold Wellness**:
The order and inbox product. Telegram identity is @THWellness_bot.
_Avoid_: THW bot, Npeppers
