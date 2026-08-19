"""TrueHold Wellness concierge portraits (Theo) for Telegram sendPhoto.

Source portraits live in inventory/assets/agent/. Framed cards are rebuilt
on demand. Telegram sendPhoto: https://core.telegram.org/bots/api#sendphoto
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from wellness_agent.inventory.graphics import (
    ASSETS,
    CREAM,
    GOLD,
    GOLD_SOFT,
    NAVY_DEEP,
    WHITE,
    fit,
    font,
    gold_bars,
    paste_logo,
    paste_overlay,
    tech_hud_overlay,
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
    return build_agent_card(pose)


def ensure_agent() -> list[Path]:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    return [build_agent_card(pose) for pose in POSES]


def build_agent_card(pose: str) -> Path:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    name = pose if pose in POSES else "wave"
    portrait = _load_portrait(name)
    if portrait is not None:
        image = _cover(portrait, SIZE)
    else:
        image = vertical_gradient(SIZE, (2, 8, 18), NAVY_DEEP)
    image = _left_scrim(image)
    image = paste_overlay(image, tech_hud_overlay(SIZE, seed=8 + POSES.index(name)))
    draw = ImageDraw.Draw(image)
    gold_bars(draw, SIZE, thickness=10)
    kicker, line = KICKERS[name]
    draw.text((56, 72), "TRUEHOLD WELLNESS  ·  TECH CONCIERGE", font=font(22, bold=True), fill=GOLD)
    draw.text((56, 120), kicker, font=font(72, bold=True), fill=WHITE)
    draw.multiline_text(
        (56, 222),
        fit(line, font(30), draw, 520),
        font=font(30),
        fill=CREAM,
        spacing=8,
    )
    draw.text((56, 620), "HUD live  ·  Tap a button  ·  Educational only", font=font(22, bold=True), fill=GOLD_SOFT)
    paste_logo(image, box=108, margin=32)
    dest = agent_card_path(name)
    image.save(dest, format="JPEG", quality=90)
    return dest


def _load_portrait(pose: str) -> Image.Image | None:
    path = portrait_path(pose)
    if not path.is_file():
        return None
    return Image.open(path).convert("RGB")


def _cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    width, height = size
    src_w, src_h = image.size
    scale = max(width / src_w, height / src_h)
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = max(resized.size[0] - width, 0) * 0.62
    top = max(resized.size[1] - height, 0) * 0.12
    box = (int(left), int(top), int(left) + width, int(top) + height)
    return resized.crop(box)


def _left_scrim(image: Image.Image) -> Image.Image:
    width, height = image.size
    scrim = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(scrim)
    for x in range(0, int(width * 0.62)):
        t = 1 - (x / (width * 0.62))
        alpha = int(210 * (t**1.15))
        draw.line((x, 0, x, height), fill=(3, 10, 24, alpha), width=1)
    return paste_overlay(image, scrim.filter(ImageFilter.GaussianBlur(radius=6)))


def main() -> int:
    for path in ensure_agent():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
