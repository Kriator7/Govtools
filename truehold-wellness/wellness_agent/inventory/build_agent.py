"""TrueHold Wellness floor-team portraits for Telegram sendPhoto.

Source portraits live in inventory/assets/agent/. Framed cards are rebuilt
on demand. Telegram sendPhoto: https://core.telegram.org/bots/api#sendphoto
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from wellness_agent.inventory.graphics import (
    ASSETS,
    CREAM,
    GOLD_SOFT,
    NAVY_DEEP,
    WHITE,
    fit,
    font,
    gold_bars,
    paste_logo,
    paste_overlay,
    tech_hud_overlay,
    theme_rgb,
    vertical_gradient,
)

PORTRAIT_DIR = ASSETS / "agent"
CARD_DIR = ASSETS / "agent_cards"
POSES = ("wave", "present", "think", "work", "cheer", "soon")
SIZE = (1280, 720)


def _member(member_id: str | None = None) -> dict[str, Any]:
    from wellness_agent.team import get_member

    return get_member(member_id)


def portrait_path(pose: str = "wave", member_id: str | None = None) -> Path:
    member = _member(member_id)
    name = pose if pose in POSES else "wave"
    posed = PORTRAIT_DIR / f"{member['id']}-{name}.jpg"
    if posed.is_file():
        return posed
    signature = PORTRAIT_DIR / f"{member['id']}.jpg"
    if signature.is_file():
        return signature
    return PORTRAIT_DIR / "theo-wave.jpg"


def agent_card_path(pose: str = "wave", member_id: str | None = None) -> Path:
    member = _member(member_id)
    name = pose if pose in POSES else "wave"
    return CARD_DIR / f"{member['id']}-{name}.jpg"


def agent_path(pose: str = "wave", member_id: str | None = None) -> Path:
    return build_agent_card(pose, member_id)


def ensure_host(member_id: str | None = None) -> list[Path]:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    return [build_agent_card(pose, member_id) for pose in POSES]


def ensure_agent() -> list[Path]:
    from wellness_agent.team import members

    CARD_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for row in members():
        paths.extend(ensure_host(row["id"]))
    return paths


def build_agent_card(pose: str, member_id: str | None = None) -> Path:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    member = _member(member_id)
    name = pose if pose in POSES else "wave"
    portrait = _load_portrait(name, member["id"])
    if portrait is not None:
        image = _cover(portrait, SIZE)
    else:
        image = vertical_gradient(SIZE, (2, 8, 18), NAVY_DEEP)
    image = _left_scrim(image)
    accent = theme_rgb(str(member.get("color") or ""))
    pose_seed = POSES.index(name) if name in POSES else 0
    image = paste_overlay(
        image,
        tech_hud_overlay(SIZE, seed=8 + pose_seed + 17 * abs(hash(member["id"])) % 50, accent=accent),
    )
    draw = ImageDraw.Draw(image)
    gold_bars(draw, SIZE, thickness=10, fill=accent)
    from wellness_agent.team import pose_line

    kicker = str(member["name"]).upper()
    line = pose_line(member, name)
    role = str(member.get("role") or "Floor host").upper()
    draw.text((56, 72), f"TRUEHOLD WELLNESS  ·  {role}", font=font(22, bold=True), fill=accent)
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
    dest = agent_card_path(name, member["id"])
    image.save(dest, format="JPEG", quality=90)
    return dest


def _load_portrait(pose: str, member_id: str) -> Image.Image | None:
    path = portrait_path(pose, member_id)
    if not path.is_file():
        return None
    return Image.open(path).convert("RGB")


def _cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    width, height = size
    src_w, src_h = image.size
    scale = max(width / src_w, height / src_h)
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    extra_w = max(resized.size[0] - width, 0)
    extra_h = max(resized.size[1] - height, 0)
    # Landscape posed shots (Theo) sit on the right; square portraits stay centered.
    right_bias = 0.62 if (src_w / max(src_h, 1)) > 1.2 else 0.50
    left = extra_w * right_bias
    top = extra_h * 0.12
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
