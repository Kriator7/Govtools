"""Build TrueHold Wellness picture-menu cards (one photo per live SKU).

Telegram sendPhoto: https://core.telegram.org/bots/api#sendphoto
"""

from __future__ import annotations

from pathlib import Path

from PIL import ImageDraw

import hashlib

from wellness_agent.catalog import products
from wellness_agent.inventory.build_brand import ensure_brand
from wellness_agent.inventory.graphics import (
    CARD_DIR,
    CREAM,
    GOLD,
    GOLD_SOFT,
    NAVY,
    NAVY_DEEP,
    WHITE,
    fit,
    font,
    gold_bars,
    molecule_overlay,
    paste_logo,
    paste_overlay,
    vertical_gradient,
)

SIZE = (960, 720)


def build_card(product: dict) -> Path:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    ensure_brand()
    path = CARD_DIR / f"{product['id']}.jpg"
    image = vertical_gradient(SIZE, NAVY_DEEP, NAVY)
    seed = int(hashlib.md5(str(product["id"]).encode("utf-8")).hexdigest()[:6], 16) % 50
    image = paste_overlay(image, molecule_overlay(SIZE, seed=seed, origin=(720, 380), scale=0.95))
    draw = ImageDraw.Draw(image)
    gold_bars(draw, SIZE, thickness=16)
    title_font = font(68, bold=True)
    vial_font = font(32, bold=True)
    small_font = font(24, bold=True)
    meta_font = font(22)
    title = fit(str(product["name"]), title_font, draw, SIZE[0] - 280)
    vial = fit(str(product["vial"]), vial_font, draw, SIZE[0] - 120)
    draw.text((56, 72), "TRUEHOLD WELLNESS", font=small_font, fill=GOLD)
    draw.multiline_text((56, 168), title, font=title_font, fill=WHITE, spacing=8)
    draw.multiline_text((56, 360), vial, font=vial_font, fill=CREAM, spacing=6)
    draw.text((56, 500), "Dry (lyophilized) vial  ·  Educational information", font=meta_font, fill=GOLD_SOFT)
    draw.text((56, 548), "Prep and local delivery: Las Vegas residents only", font=meta_font, fill=CREAM)
    draw.text((56, 620), "Tap Order  ·  Sheet  ·  Prep", font=small_font, fill=GOLD)
    paste_logo(image, box=128, margin=40)
    image.save(path, format="JPEG", quality=92)
    return path


def ensure_cards() -> list[Path]:
    ensure_brand()
    return [
        build_card(item) if not (CARD_DIR / f"{item['id']}.jpg").is_file() else CARD_DIR / f"{item['id']}.jpg"
        for item in products()
    ]


def card_path(product: dict) -> Path:
    path = CARD_DIR / f"{product['id']}.jpg"
    if not path.is_file():
        return build_card(product)
    return path


def main() -> int:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    for path in ensure_brand():
        print(path)
    for item in products():
        built = build_card(item)
        print(built)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
