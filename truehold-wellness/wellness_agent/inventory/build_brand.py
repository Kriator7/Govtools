"""Build TrueHold Wellness intro hero and service banners.

Uses the official `assets/logo.jpeg` when present. Telegram sendPhoto:
https://core.telegram.org/bots/api#sendphoto
"""

from __future__ import annotations

from pathlib import Path

from PIL import ImageDraw

from wellness_agent.inventory.graphics import (
    ASSETS,
    CREAM,
    GOLD,
    GOLD_SOFT,
    HERO_PATH,
    LOGO_PATH,
    NAVY,
    NAVY_DEEP,
    NAVY_MID,
    SERVICE_PATH,
    TEAL,
    WHITE,
    brand_mark,
    fit,
    font,
    gold_bars,
    molecule_overlay,
    official_logo,
    paste_logo,
    paste_overlay,
    vertical_gradient,
)


def logo_path() -> Path:
    existing = official_logo()
    if existing is not None:
        return existing
    return build_logo()


def hero_path() -> Path:
    if not HERO_PATH.is_file():
        build_hero()
    return HERO_PATH


def service_path() -> Path:
    if not SERVICE_PATH.is_file():
        build_service()
    return SERVICE_PATH


def ensure_brand() -> list[Path]:
    ASSETS.mkdir(parents=True, exist_ok=True)
    return [logo_path(), build_hero(), build_service()]


def build_logo() -> Path:
    """Fallback mark when the official logo.jpeg is not in the tree."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    size = (640, 640)
    image = vertical_gradient(size, NAVY_DEEP, NAVY_MID)
    image = paste_overlay(image, molecule_overlay(size, seed=3, origin=(320, 300), scale=0.85))
    draw = ImageDraw.Draw(image)
    gold_bars(draw, size, thickness=18)
    cx, cy, ring = 320, 292, 168
    draw.ellipse((cx - ring, cy - ring, cx + ring, cy + ring), outline=GOLD, width=6)
    draw.ellipse((cx - ring + 14, cy - ring + 14, cx + ring - 14, cy + ring - 14), outline=TEAL, width=2)
    brand_mark(draw, cx, cy, 86)
    title = font(36, bold=True)
    small = font(22, bold=True)
    draw.text((320, 488), "TRUEHOLD", font=title, fill=WHITE, anchor="mm")
    draw.text((320, 534), "WELLNESS", font=small, fill=GOLD, anchor="mm")
    image.save(LOGO_PATH, format="JPEG", quality=92)
    return LOGO_PATH


def build_hero() -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    size = (1280, 720)
    image = vertical_gradient(size, NAVY_DEEP, NAVY)
    image = paste_overlay(image, molecule_overlay(size, seed=11, origin=(920, 340), scale=1.15))
    draw = ImageDraw.Draw(image)
    gold_bars(draw, size, thickness=18)
    kicker = font(28, bold=True)
    title = font(64, bold=True)
    sub = font(30)
    draw.text((64, 86), "TRUEHOLD WELLNESS", font=kicker, fill=GOLD)
    draw.multiline_text(
        (64, 160),
        fit("Research peptides. Clear process.", title, draw, 720),
        font=title,
        fill=WHITE,
        spacing=10,
    )
    draw.multiline_text(
        (64, 360),
        "Las Vegas residents only\nPrep and local delivery in Las Vegas\nDry (lyophilized) vials only",
        font=sub,
        fill=CREAM,
        spacing=10,
    )
    draw.text((64, 620), "Educational information  ·  Team consult  ·  Required documentation", font=kicker, fill=GOLD_SOFT)
    paste_logo(image, box=176, margin=40)
    image.save(HERO_PATH, format="JPEG", quality=92)
    return HERO_PATH


def build_service() -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    size = (1280, 560)
    image = vertical_gradient(size, NAVY, NAVY_DEEP)
    image = paste_overlay(image, molecule_overlay(size, seed=19, origin=(980, 280), scale=1.0))
    draw = ImageDraw.Draw(image)
    gold_bars(draw, size, thickness=14)
    kicker = font(26, bold=True)
    title = font(48, bold=True)
    sub = font(28)
    draw.text((64, 70), "TRUEHOLD WELLNESS", font=kicker, fill=GOLD)
    draw.text((64, 130), "Local prep  ·  Dry vials", font=title, fill=WHITE)
    draw.multiline_text(
        (64, 220),
        "Prep and local delivery: Las Vegas residents only.\n"
        "Shipping: dry (lyophilized) vials only.\n"
        "The team confirms, consults, and completes required documentation.",
        font=sub,
        fill=CREAM,
        spacing=10,
    )
    paste_logo(image, box=140, margin=36)
    image.save(SERVICE_PATH, format="JPEG", quality=92)
    return SERVICE_PATH


def main() -> int:
    for path in ensure_brand():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
