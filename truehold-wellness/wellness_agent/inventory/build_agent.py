"""TrueHold Wellness concierge portraits (Theo) for Telegram sendPhoto.

Source portraits live in inventory/assets/agent/. Framed cards are rebuilt
on demand. Telegram sendPhoto: https://core.telegram.org/bots/api#sendphoto
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from wellness_agent.inventory.graphics import (
    ASSETS,
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

PORTRAIT_DIR = ASSETS / "agent"
CARD_DIR = ASSETS / "agent_cards"
POSES = ("wave", "present", "cheer", "think")
SIZE = (1280, 720)
KICKERS = {
    "wave": ("THEO", "Good to see you."),
    "present": ("THEO", "Tap a name — I will pull that tile."),
    "cheer": ("THEO", "Logged. The team takes it from here."),
    "think": ("THEO", "Locked sheet has the details."),
}


def portrait_path(pose: str) -> Path:
    name = pose if pose in POSES else "wave"
    return PORTRAIT_DIR / f"theo-{name}.jpg"


def agent_card_path(pose: str) -> Path:
    name = pose if pose in POSES else "wave"
    return CARD_DIR / f"theo-{name}.jpg"


def agent_path(pose: str = "wave") -> Path:
    path = agent_card_path(pose)
    if not path.is_file():
        return build_agent_card(pose)
    return path


def ensure_agent() -> list[Path]:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    return [build_agent_card(pose) for pose in POSES]


def build_agent_card(pose: str) -> Path:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    name = pose if pose in POSES else "wave"
    image = vertical_gradient(SIZE, NAVY_DEEP, NAVY)
    image = paste_overlay(image, molecule_overlay(SIZE, seed=21, origin=(980, 360), scale=1.05))
    portrait = _load_portrait(name)
    if portrait is not None:
        image = _paste_portrait(image, portrait)
    draw = ImageDraw.Draw(image)
    gold_bars(draw, SIZE, thickness=16)
    kicker, line = KICKERS[name]
    draw.text((56, 72), "TRUEHOLD WELLNESS", font=font(26, bold=True), fill=GOLD)
    draw.text((56, 128), kicker, font=font(72, bold=True), fill=WHITE)
    draw.multiline_text(
        (56, 230),
        fit(line, font(32), draw, 560),
        font=font(32),
        fill=CREAM,
        spacing=8,
    )
    draw.text((56, 620), "Colorful buttons below  ·  Educational only", font=font(24, bold=True), fill=GOLD_SOFT)
    paste_logo(image, box=120, margin=36)
    dest = agent_card_path(name)
    image.save(dest, format="JPEG", quality=90)
    return dest


def _load_portrait(pose: str) -> Image.Image | None:
    path = portrait_path(pose)
    if not path.is_file():
        return None
    return Image.open(path).convert("RGB")


def _paste_portrait(base: Image.Image, portrait: Image.Image) -> Image.Image:
    height = SIZE[1] - 32
    portrait = portrait.copy()
    portrait.thumbnail((height, height))
    x = SIZE[0] - portrait.size[0] - 24
    y = (SIZE[1] - portrait.size[1]) // 2
    mask = Image.new("L", portrait.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *portrait.size), radius=36, fill=255)
    base.paste(portrait, (x, y), mask)
    return base


def main() -> int:
    for path in ensure_agent():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
