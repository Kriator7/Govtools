#!/usr/bin/env python3
"""Helpers for Grill with Docs: glossary map, term upsert, ADR numbering."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = ROOT / "GLOSSARY-MAP.md"
SKILL_PATH = ROOT / ".agents" / "skills" / "grill-with-docs" / "SKILL.md"

CONTEXT_RE = re.compile(
    r"^- \[([^\]]+)\]\(([^)]+)\):\s*(.+)$",
    re.MULTILINE,
)
ADR_HINT_RE = re.compile(r"ADRs:\s*`([^`]+)`")
TERM_RE = re.compile(
    r"^\*\*(.+?)\*\*:\s*\n((?:.*\n)*?)(?=^\*\*|\Z)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Context:
    id: str
    name: str
    glossary: Path
    adr_dir: Path
    description: str

    @property
    def root(self) -> Path:
        if self.glossary.name == "GLOSSARY.md" and self.glossary.parent == ROOT:
            return ROOT
        return self.glossary.parent


def display_path(path: Path, *, root: Path = ROOT) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def slug_from_glossary(glossary: Path) -> str:
    if glossary.parent == ROOT:
        return "govtools"
    return glossary.parent.name.replace("_", "-")


def load_map(text: str | None = None, *, root: Path = ROOT) -> list[Context]:
    source = MAP_PATH.read_text(encoding="utf-8") if text is None else text
    found: list[Context] = []
    for name, rel, rest in CONTEXT_RE.findall(source):
        glossary = (root / rel).resolve()
        hint = ADR_HINT_RE.search(rest)
        if hint:
            adr_dir = (root / hint.group(1)).resolve()
        elif glossary.parent == root:
            adr_dir = (root / "docs" / "adr").resolve()
        else:
            adr_dir = (glossary.parent / "docs" / "adr").resolve()
        found.append(
            Context(
                id=slug_from_glossary(glossary),
                name=name.strip(),
                glossary=glossary,
                adr_dir=adr_dir,
                description=rest.strip(),
            )
        )
    if not found:
        raise SystemExit(f"no contexts found in {MAP_PATH}")
    return found


def get_context(contexts: list[Context], key: str) -> Context:
    needle = key.strip().lower()
    for ctx in contexts:
        if needle in {ctx.id, ctx.name.lower(), ctx.root.name.lower()}:
            return ctx
    raise SystemExit(
        f"unknown context {key!r}; known: " + ", ".join(ctx.id for ctx in contexts)
    )


def resolve_path(contexts: list[Context], path: str, *, root: Path = ROOT) -> Context:
    target = Path(path)
    if not target.is_absolute():
        target = (root / target).resolve()
    else:
        target = target.resolve()
    ranked: list[tuple[int, Context]] = []
    for ctx in contexts:
        try:
            target.relative_to(ctx.root)
        except ValueError:
            continue
        ranked.append((len(ctx.root.parts), ctx))
    if not ranked:
        raise SystemExit(f"path {path} is not inside a known glossary context")
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def next_adr_number(adr_dir: Path) -> int:
    highest = 0
    if adr_dir.is_dir():
        for path in adr_dir.glob("*.md"):
            match = re.match(r"^(\d+)-", path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "decision"


def parse_terms(text: str) -> dict[str, dict[str, str]]:
    terms: dict[str, dict[str, str]] = {}
    language = text.split("## Language", 1)
    body = language[1] if len(language) == 2 else text
    for match in TERM_RE.finditer(body):
        name = match.group(1).strip()
        block = match.group(2)
        avoid = ""
        alias = ""
        definition_lines: list[str] = []
        for raw in block.splitlines():
            line = raw.strip()
            if line.lower().startswith("_avoid_:"):
                avoid = line.split(":", 1)[1].strip()
            elif line.lower().startswith("_alias_:"):
                alias = line.split(":", 1)[1].strip()
            elif line:
                definition_lines.append(line)
        terms[name] = {
            "definition": " ".join(definition_lines).strip(),
            "avoid": avoid,
            "alias": alias,
        }
    return terms


def render_entry(term: str, definition: str, avoid: str, alias: str) -> str:
    lines = [f"**{term}**:", definition.strip()]
    if avoid.strip():
        lines.append(f"_Avoid_: {avoid.strip()}")
    if alias.strip():
        lines.append(f"_Alias_: {alias.strip()}")
    return "\n".join(lines) + "\n"


def upsert_term(
    glossary: Path,
    *,
    context_name: str,
    overview: str,
    term: str,
    definition: str,
    avoid: str = "",
    alias: str = "",
) -> str:
    if not definition.strip():
        raise SystemExit("definition is required")
    if glossary.is_file():
        text = glossary.read_text(encoding="utf-8")
    else:
        text = f"# {context_name}\n\n{overview}\n\n## Language\n"
        glossary.parent.mkdir(parents=True, exist_ok=True)
    if "## Language" not in text:
        text = text.rstrip() + "\n\n## Language\n"
    entry = render_entry(term, definition, avoid, alias)
    pattern = re.compile(
        rf"^\*\*{re.escape(term)}\*\*:\s*\n(?:.*\n)*?(?=^\*\*|\Z)",
        re.MULTILINE,
    )
    if pattern.search(text):
        updated = pattern.sub(entry + "\n", text, count=1)
    else:
        updated = text.rstrip() + "\n\n" + entry
    glossary.write_text(updated.rstrip() + "\n", encoding="utf-8")
    return "updated" if pattern.search(text) else "created"


def write_adr(adr_dir: Path, title: str, body: str) -> Path:
    if not title.strip() or not body.strip():
        raise SystemExit("ADR title and body are required")
    adr_dir.mkdir(parents=True, exist_ok=True)
    number = next_adr_number(adr_dir)
    path = adr_dir / f"{number:04d}-{slugify(title)}.md"
    path.write_text(f"# {title.strip()}\n\n{body.strip()}\n", encoding="utf-8")
    return path


def check_glossary(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return errors
    text = path.read_text(encoding="utf-8")
    if not text.startswith("# "):
        errors.append(f"{display_path(path)}: missing top-level heading")
    if "## Language" not in text:
        errors.append(f"{display_path(path)}: missing ## Language")
    terms = parse_terms(text)
    if path.is_file() and "## Language" in text and not terms:
        errors.append(f"{display_path(path)}: Language section has no terms")
    for name, payload in terms.items():
        if not payload["definition"]:
            errors.append(f"{display_path(path)}: {name!r} has no definition")
        if len(payload["definition"].split()) > 60:
            errors.append(
                f"{display_path(path)}: {name!r} definition is too long for a glossary"
            )
    return errors


def check_skill() -> list[str]:
    errors: list[str] = []
    if not SKILL_PATH.is_file():
        return [f"missing skill at {SKILL_PATH.relative_to(ROOT)}"]
    text = SKILL_PATH.read_text(encoding="utf-8")
    if "Call the Skill tool twice" in text and "design tree" not in text.lower():
        errors.append("grill-with-docs SKILL.md is a one-line delegation; it must be self-contained")
    required = (
        "one question per turn",
        "GLOSSARY.md",
        "Hard to reverse",
        "Do not implement",
        "AskQuestion",
    )
    for snippet in required:
        if snippet not in text:
            errors.append(f"SKILL.md is missing required guidance: {snippet}")
    return errors


def check_repo() -> list[str]:
    errors: list[str] = []
    if not MAP_PATH.is_file():
        return ["GLOSSARY-MAP.md is missing"]
    errors.extend(check_skill())
    contexts = load_map()
    ids = [ctx.id for ctx in contexts]
    for required in ("govtools", "mr-north", "realtor-agent", "truehold-wellness"):
        if required not in ids:
            errors.append(f"GLOSSARY-MAP.md is missing context {required}")
    for ctx in contexts:
        errors.extend(check_glossary(ctx.glossary))
        if ctx.adr_dir.is_dir():
            numbers = []
            for path in sorted(ctx.adr_dir.glob("*.md")):
                match = re.match(r"^(\d+)-.+\.md$", path.name)
                if not match:
                    errors.append(f"{path.relative_to(ROOT)}: ADR filename must be NNNN-slug.md")
                    continue
                numbers.append(int(match.group(1)))
                text = path.read_text(encoding="utf-8")
                if not text.startswith("# "):
                    errors.append(f"{path.relative_to(ROOT)}: ADR must start with a title heading")
            if numbers != sorted(numbers):
                errors.append(f"{ctx.adr_dir.relative_to(ROOT)}: ADR numbers are not sorted")
    return errors


def cmd_map(_args: argparse.Namespace) -> int:
    for ctx in load_map():
        glossary_rel = ctx.glossary.relative_to(ROOT)
        adr_rel = ctx.adr_dir.relative_to(ROOT)
        exists = "yes" if ctx.glossary.is_file() else "lazy"
        print(f"{ctx.id}\t{ctx.name}\t{glossary_rel}\t{adr_rel}\t{exists}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    contexts = load_map()
    if args.context:
        ctx = get_context(contexts, args.context)
    elif args.path:
        ctx = resolve_path(contexts, args.path)
    else:
        raise SystemExit("resolve needs --context or --path")
    print(f"{ctx.id}\t{ctx.name}\t{ctx.glossary.relative_to(ROOT)}\t{ctx.adr_dir.relative_to(ROOT)}")
    return 0


def cmd_next_adr(args: argparse.Namespace) -> int:
    ctx = get_context(load_map(), args.context)
    number = next_adr_number(ctx.adr_dir)
    print(f"{number:04d}\t{ctx.adr_dir.relative_to(ROOT)}")
    return 0


def cmd_upsert(args: argparse.Namespace) -> int:
    ctx = get_context(load_map(), args.context)
    action = upsert_term(
        ctx.glossary,
        context_name=ctx.name,
        overview=ctx.description.split("ADRs:")[0].strip().rstrip("."),
        term=args.term,
        definition=args.definition,
        avoid=args.avoid or "",
        alias=args.alias or "",
    )
    print(f"{action}\t{ctx.glossary.relative_to(ROOT)}\t{args.term}")
    return 0


def cmd_write_adr(args: argparse.Namespace) -> int:
    ctx = get_context(load_map(), args.context)
    path = write_adr(ctx.adr_dir, args.title, args.body)
    print(path.relative_to(ROOT))
    return 0


def cmd_check(_args: argparse.Namespace) -> int:
    errors = check_repo()
    if errors:
        sys.stderr.write("GRILL DOCS CHECK FAILED\n")
        for item in errors:
            sys.stderr.write(f"- {item}\n")
        return 1
    print("grill-with-docs artifacts ok")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("map", help="list glossary contexts").set_defaults(func=cmd_map)

    resolve = sub.add_parser("resolve", help="resolve a context from --context or --path")
    resolve.add_argument("--context")
    resolve.add_argument("--path")
    resolve.set_defaults(func=cmd_resolve)

    nxt = sub.add_parser("next-adr", help="print the next ADR number for a context")
    nxt.add_argument("--context", required=True)
    nxt.set_defaults(func=cmd_next_adr)

    upsert = sub.add_parser("upsert-term", help="write a glossary term immediately")
    upsert.add_argument("--context", required=True)
    upsert.add_argument("--term", required=True)
    upsert.add_argument("--definition", required=True)
    upsert.add_argument("--avoid", default="")
    upsert.add_argument("--alias", default="")
    upsert.set_defaults(func=cmd_upsert)

    adr = sub.add_parser("write-adr", help="write the next ADR in a context")
    adr.add_argument("--context", required=True)
    adr.add_argument("--title", required=True)
    adr.add_argument("--body", required=True)
    adr.set_defaults(func=cmd_write_adr)

    sub.add_parser("check", help="validate map, skill, glossaries, and ADRs").set_defaults(
        func=cmd_check
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
