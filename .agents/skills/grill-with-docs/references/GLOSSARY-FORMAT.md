# GLOSSARY.md format

Adapted from Matt Pocock's domain-modeling skill (MIT).

## Structure

```md
# {Context Name}

{One or two sentences: what this context is and why it exists.}

## Language

**Interest order**:
A customer request logged from Telegram before staff confirm fulfillment.
_Avoid_: Purchase, checkout
_Alias_: record_order_row

**On-hand**:
The live vial count for a catalog SKU after interest-order decrements.
_Avoid_: Inventory, stock level
```

## Rules

- **Be opinionated.** When several words name the same concept, pick one and
  list the rest under `_Avoid_`.
- **Keep definitions tight.** One or two sentences. Define what it *is*, not
  what it does.
- **Project terms only.** Timeouts, error types, and other general programming
  ideas do not belong even if the code uses them constantly.
- **Group under subheadings** when clusters appear. A flat list is fine.
- `_Alias_` is the only place code names appear. Class, function, or enum
  names — no file paths, no line numbers. Omit `_Alias_` if unimplemented.
- Skip `_Avoid_` when there are no rejected synonyms.

## This repo

`GLOSSARY-MAP.md` at the root lists four contexts. Write terms into the
matching file, creating it on the first resolved term:

| Context | Glossary | ADRs |
| --- | --- | --- |
| Govtools repo | `GLOSSARY.md` | `docs/adr/` |
| Mr North | `mr_north/GLOSSARY.md` | `mr_north/docs/adr/` |
| Realtor acquisition | `realtor-agent/GLOSSARY.md` | `realtor-agent/docs/adr/` |
| TrueHold Wellness | `truehold-wellness/GLOSSARY.md` | `truehold-wellness/docs/adr/` |

Do not create empty glossaries in advance.
