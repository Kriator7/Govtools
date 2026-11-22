# ADR format

Adapted from Matt Pocock's domain-modeling skill (MIT).

Architecture Decision Records live in the context's `docs/adr/` directory and
use sequential numbering: `0001-slug.md`, `0002-slug.md`. Create the directory
on the first ADR that clears the bar.

## Template

```md
# {Short title of the decision}

{1-3 sentences: what's the context, what did we decide, and why.}
```

An ADR can be a single paragraph. The value is recording *that* a decision was
made and *why*, not filling out sections.

## Optional sections

Include these only when they add something a future reader would miss:

- **Status** (`proposed` / `accepted` / `deprecated` / `superseded by ADR-NNNN`)
- **Considered Options** — rejected alternatives worth remembering
- **Consequences** — non-obvious downstream effects

## Numbering

Scan that context's `docs/adr/` for the highest existing number and add one.
Use `python scripts/grill_docs.py next-adr --context <id>`.

## When to write

All three must be true:

1. **Hard to reverse** — changing your mind later is costly.
2. **Surprising without context** — a future reader will look at the code and
   wonder why it is this way.
3. **A real trade-off** — genuine alternatives existed, and you picked one.

Skip it if it is easy to reverse, unsurprising, or there was no real
alternative. "We did the obvious thing" is not an ADR.

### What qualifies

- Architectural shape (monorepo vs packages, write/read models).
- Integration patterns between contexts.
- Technology choices with lock-in (database, auth, deploy target).
- Boundary and scope decisions, including explicit no-s.
- Deliberate deviations from the obvious path.
- Constraints the code cannot show (compliance, partner SLAs).
- Rejected alternatives whose rejection is non-obvious.

In this repo, "the three products do not share bots, databases, or application
code" is an ADR. "Use pytest" is not.
