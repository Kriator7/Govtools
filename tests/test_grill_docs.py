"""Grill with Docs skill, glossary map, and helpers."""

from pathlib import Path

from scripts.grill_docs import (
    SKILL_PATH,
    check_glossary,
    check_repo,
    get_context,
    load_map,
    main,
    next_adr_number,
    parse_terms,
    resolve_path,
    slugify,
    upsert_term,
    write_adr,
)

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / ".agents" / "skills" / "grill-with-docs"


def test_skill_is_self_contained_and_discoverable():
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert SKILL_PATH.is_file()
    assert text.startswith("---\nname: grill-with-docs")
    assert "disable-model-invocation: true" in text
    assert "Call the Skill tool twice" not in text
    assert "one question per turn" in text
    assert "Do not implement" in text
    assert (SKILL_DIR / "references" / "GLOSSARY-FORMAT.md").is_file()
    assert (SKILL_DIR / "references" / "ADR-FORMAT.md").is_file()
    assert (SKILL_DIR / "ATTRIBUTION.md").is_file()
    assert "Matt Pocock" in (SKILL_DIR / "ATTRIBUTION.md").read_text(encoding="utf-8")


def test_agents_md_points_at_the_skill():
    notes = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert ".agents/skills/grill-with-docs/SKILL.md" in notes
    assert "one" in notes.lower()
    assert "shared understanding" in notes


def test_map_lists_the_four_contexts():
    contexts = load_map()
    ids = [ctx.id for ctx in contexts]
    assert ids == ["govtools", "mr-north", "realtor-agent", "truehold-wellness"]
    wellness = get_context(contexts, "truehold-wellness")
    assert wellness.glossary == ROOT / "truehold-wellness" / "GLOSSARY.md"
    assert wellness.adr_dir == ROOT / "truehold-wellness" / "docs" / "adr"
    repo = get_context(contexts, "Govtools repo")
    assert repo.glossary == ROOT / "GLOSSARY.md"
    assert repo.adr_dir == ROOT / "docs" / "adr"


def test_resolve_path_prefers_the_product_folder():
    contexts = load_map()
    wellness = resolve_path(contexts, "truehold-wellness/wellness_agent/stock.py")
    assert wellness.id == "truehold-wellness"
    north = resolve_path(contexts, "mr_north/hourly.py")
    assert north.id == "mr-north"
    root = resolve_path(contexts, "scripts/grill_docs.py")
    assert root.id == "govtools"


def test_root_glossary_is_vocabulary_not_a_spec():
    terms = parse_terms((ROOT / "GLOSSARY.md").read_text(encoding="utf-8"))
    assert "Protected agent" in terms
    assert "Grill with Docs" in terms
    assert "TrueHold Wellness" in terms
    assert "Desktop Jarvis" in terms
    assert "implementation detail" not in terms["Grill with Docs"]["definition"].lower()
    assert not check_glossary(ROOT / "GLOSSARY.md")


def test_existing_adr_is_the_product_split():
    adr = ROOT / "docs" / "adr" / "0001-three-independent-products.md"
    text = adr.read_text(encoding="utf-8")
    assert text.startswith("# Three independent products")
    assert "do not share Telegram bots" in text
    jarvis = ROOT / "docs" / "adr" / "0002-desktop-jarvis-stays-outside-this-repository.md"
    assert "Do not clone it into this repo" in jarvis.read_text(encoding="utf-8")
    assert next_adr_number(ROOT / "docs" / "adr") == 3


def test_upsert_term_creates_and_replaces(tmp_path: Path):
    glossary = tmp_path / "GLOSSARY.md"
    created = upsert_term(
        glossary,
        context_name="Fixture",
        overview="A test context.",
        term="Interest order",
        definition="A customer request logged before fulfillment.",
        avoid="purchase",
        alias="record_order_row",
    )
    assert created == "created"
    terms = parse_terms(glossary.read_text(encoding="utf-8"))
    assert terms["Interest order"]["avoid"] == "purchase"
    replaced = upsert_term(
        glossary,
        context_name="Fixture",
        overview="A test context.",
        term="Interest order",
        definition="A Telegram request that has not been fulfilled yet.",
        avoid="purchase, checkout",
    )
    assert replaced == "updated"
    terms = parse_terms(glossary.read_text(encoding="utf-8"))
    assert terms["Interest order"]["definition"].startswith("A Telegram request")
    assert terms["Interest order"]["avoid"] == "purchase, checkout"


def test_write_adr_numbers_sequentially(tmp_path: Path):
    adr_dir = tmp_path / "docs" / "adr"
    first = write_adr(adr_dir, "Use events", "Ordering emits events; billing consumes them.")
    second = write_adr(
        adr_dir,
        "Keep products isolated",
        "Wellness never reads Mr North tokens.",
    )
    assert first.name == "0001-use-events.md"
    assert second.name == "0002-keep-products-isolated.md"
    assert slugify("Low-stock alerts") == "low-stock-alerts"


def test_check_glossary_rejects_empty_language(tmp_path: Path):
    path = tmp_path / "GLOSSARY.md"
    path.write_text("# Demo\n\n## Language\n\n", encoding="utf-8")
    errors = check_glossary(path)
    assert errors
    assert any("no terms" in item for item in errors)


def test_check_and_cli_map_pass_on_the_repo(capsys):
    assert check_repo() == []
    assert main(["check"]) == 0
    assert main(["map"]) == 0
    mapped = capsys.readouterr().out
    assert "truehold-wellness" in mapped
    assert main(["resolve", "--path", "truehold-wellness/wellness_agent/stock.py"]) == 0
    resolved = capsys.readouterr().out
    assert resolved.startswith("truehold-wellness\t")
    assert main(["next-adr", "--context", "govtools"]) == 0
    assert capsys.readouterr().out.startswith("0003\t")


def test_stock_fact_is_readable_so_grilling_can_look_it_up():
    stock = (
        ROOT / "truehold-wellness" / "wellness_agent" / "stock.py"
    ).read_text(encoding="utf-8")
    readme = (ROOT / "truehold-wellness" / "README.md").read_text(encoding="utf-8")
    assert "Interest orders decrement on-hand" in stock
    assert "decrements on-hand inventory" in readme
