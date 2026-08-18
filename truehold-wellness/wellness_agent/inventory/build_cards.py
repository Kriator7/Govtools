"""Build TrueHold Wellness picture-menu cards (one photo per live SKU).

Telegram sendPhoto: https://core.telegram.org/bots/api#sendphoto
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from wellness_agent.catalog import products

ROOT = Path(__file__).resolve().parent
CARD_DIR = ROOT / "cards"
LOGO = ROOT / "assets" / "logo.jpeg"

NAVY = (9, 43, 87)
GOLD = (201, 154, 66)
CREAM = (247, 243, 233)
WHITE = (255, 255, 255)
SIZE = (960, 720)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf",
    )
    roots = (
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation"),
        Path("/usr/share/fonts/truetype/freefont"),
    )
    for root in roots:
        for name in names:
            path = root / name
            if path.is_file():
                return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _fit(text: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines[:3])


def build_card(product: dict) -> Path:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    path = CARD_DIR / f"{product['id']}.jpg"
    image = Image.new("RGB", SIZE, NAVY)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, SIZE[0], 18), fill=GOLD)
    draw.rectangle((0, SIZE[1] - 18, SIZE[0], SIZE[1]), fill=GOLD)
    title_font = _font(72, bold=True)
    vial_font = _font(36, bold=True)
    small_font = _font(28)
    title = _fit(str(product["name"]), title_font, draw, SIZE[0] - 120)
    vial = _fit(str(product["vial"]), vial_font, draw, SIZE[0] - 120)
    draw.text((60, 80), "TRUEHOLD WELLNESS", font=small_font, fill=GOLD)
    draw.multiline_text((60, 200), title, font=title_font, fill=WHITE, spacing=8)
    draw.multiline_text((60, 400), vial, font=vial_font, fill=CREAM, spacing=6)
    draw.text((60, 560), "Tap This one on the photo you want.", font=small_font, fill=GOLD)
    if LOGO.is_file():
        logo = Image.open(LOGO).convert("RGB")
        logo.thumbnail((140, 140))
        image.paste(logo, (SIZE[0] - logo.size[0] - 48, 48))
    image.save(path, format="JPEG", quality=90)
    return path


def ensure_cards() -> list[Path]:
    return [build_card(item) if not (CARD_DIR / f"{item['id']}.jpg").is_file() else CARD_DIR / f"{item['id']}.jpg" for item in products()]


def card_path(product: dict) -> Path:
    path = CARD_DIR / f"{product['id']}.jpg"
    if not path.is_file():
        return build_card(product)
    return path


def main() -> int:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    for item in products():
        built = build_card(item)
        print(built)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
