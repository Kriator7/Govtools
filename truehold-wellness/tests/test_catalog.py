from wellness_agent.catalog import UnknownProductError, find_product, format_catalog, pdf_path, products
from wellness_agent.cli import main
from wellness_agent.telegram_inbound import handle_telegram_update


class _FakeTelegram:
    def __init__(self) -> None:
        self.sent = []

    def send_message(self, chat_id, text, reply_markup=None):
        self.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        return {"ok": True}

    def send_document(self, chat_id, path, caption=""):
        self.sent.append({"chat_id": chat_id, "document": str(path), "caption": caption})
        return {"ok": True}

    def send_photo(self, chat_id, path, caption="", reply_markup=None):
        self.sent.append({"chat_id": chat_id, "photo": str(path), "caption": caption, "reply_markup": reply_markup})
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=None):
        return {"ok": True}


def test_live_shop_inventory_has_eight_skus_with_pdfs():
    items = products()
    ids = [item["id"] for item in items]
    assert ids == [
        "tirzepatide",
        "retatrutide",
        "semax",
        "nad",
        "klow",
        "mots-c",
        "ss-31",
        "ghk-cu",
    ]
    for item in items:
        path = pdf_path(item)
        assert path.is_file()
        assert path.suffix == ".pdf"
        assert path.stat().st_size > 1000


def test_find_product_aliases():
    assert find_product("tirz")["id"] == "tirzepatide"
    assert find_product("NAD+")["id"] == "nad"
    assert find_product("reta")["id"] == "retatrutide"
    assert find_product("GHK-Cu")["id"] == "ghk-cu"
    assert find_product("ss31")["id"] == "ss-31"


def test_unknown_product_is_rejected():
    try:
        find_product("hormuz-catalyst")
        raise AssertionError("expected UnknownProductError")
    except UnknownProductError as exc:
        assert "catalog" in str(exc)


def test_catalog_cli(capsys):
    assert main(["catalog"]) == 0
    out = capsys.readouterr().out
    assert "KLOW" in out
    assert "MOTS-c" in out
    assert "SS-31" in out
    assert "GHK-Cu" in out
    assert "Tirzepatide" in out


def test_product_cli(capsys):
    assert main(["product", "klow"]) == 0
    assert "klow.pdf" in capsys.readouterr().out


def test_telegram_catalog_and_product_sheet():
    tg = _FakeTelegram()
    catalog = handle_telegram_update(
        {"message": {"text": "/catalog", "chat": {"id": 7}, "from": {"id": 7}}},
        tg,
    )
    assert catalog["action"] == "menu"
    product = handle_telegram_update(
        {"message": {"text": "/product klow", "chat": {"id": 7}, "from": {"id": 7}}},
        tg,
    )
    assert product == {"ok": True, "action": "product", "chat_id": "7", "product": "klow"}
    docs = [item for item in tg.sent if "document" in item]
    assert docs
    assert docs[0]["document"].endswith("klow.pdf")
    assert "Educational only" in docs[0]["caption"]


def test_generated_sheets_are_educational_only():
    from pypdf import PdfReader

    for sku in ("klow", "mots-c", "ss-31", "ghk-cu"):
        reader = PdfReader(str(pdf_path(find_product(sku))))
        text = "\n".join((page.extract_text() or "") for page in reader.pages).lower()
        assert "educational information only" in text
        assert "does not provide dosing" in text
        assert "25 units" not in text
        assert "draw 2 ml" not in text


def test_picture_menu_cards_exist_for_every_sku():
    from wellness_agent.inventory.build_cards import card_path, ensure_cards

    ensure_cards()
    for item in products():
        path = card_path(item)
        assert path.is_file()
        assert path.suffix == ".jpg"
        assert path.stat().st_size > 1000


def test_brand_graphics_exist():
    from wellness_agent.inventory.build_brand import ensure_brand, hero_path, logo_path, service_path

    ensure_brand()
    for path in (logo_path(), hero_path(), service_path()):
        assert path.is_file()
        assert path.suffix.lower() in {".jpg", ".jpeg"}
        assert path.stat().st_size > 1000


def test_catalog_states_las_vegas_and_dry_vials():
    text = format_catalog().lower()
    assert "las vegas" in text
    assert "dry vials" in text
    assert "waiver" not in text
