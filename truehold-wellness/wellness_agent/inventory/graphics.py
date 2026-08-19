"""Shared navy/gold molecule drawing for TrueHold Wellness Telegram graphics."""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
CARD_DIR = ROOT / "cards"

NAVY = (8, 26, 54)
NAVY_MID = (11, 42, 86)
NAVY_DEEP = (4, 14, 32)
GOLD = (201, 154, 66)
GOLD_SOFT = (168, 132, 62)
CREAM = (247, 243, 233)
WHITE = (255, 255, 255)
TEAL = (92, 174, 196)


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf",
    )
    roots = (
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation"),
        Path("/usr/share/fonts/truetype/freefont"),
    )
    for folder in roots:
        for name in names:
            path = folder / name
            if path.is_file():
                return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def fit(text: str, typeface: ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_width: int) -> str:
    if draw.textlength(text, font=typeface) <= max_width:
        return text
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=typeface) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines[:3])


def vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    width, height = size
    strip = Image.new("RGB", (1, height), top)
    pixels = strip.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        pixels[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return strip.resize((width, height), Image.Resampling.BILINEAR)


def _hex_vertices(cx: float, cy: float, radius: float) -> list[tuple[float, float]]:
    return [
        (
            cx + radius * math.cos(math.radians(60 * i - 30)),
            cy + radius * math.sin(math.radians(60 * i - 30)),
        )
        for i in range(6)
    ]


def molecule_overlay(
    size: tuple[int, int],
    *,
    seed: int = 7,
    origin: tuple[float, float] | None = None,
    scale: float = 1.0,
) -> Image.Image:
    """Clean high-tech hex/molecule lattice. Not a product photo."""
    width, height = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    rng = random.Random(seed)
    ox, oy = origin if origin is not None else (width * 0.62, height * 0.48)
    radius = min(width, height) * 0.11 * scale
    cols, rows = 7, 6
    centers: list[tuple[float, float]] = []
    for col in range(cols):
        for row in range(rows):
            cx = ox + (col - cols / 2) * radius * 1.55
            cy = oy + (row - rows / 2) * radius * math.sqrt(3) + (radius * 0.78 if col % 2 else 0)
            if -radius < cx < width + radius and -radius < cy < height + radius:
                centers.append((cx, cy))

    gold = (*GOLD, 92)
    teal = (*TEAL, 70)
    for cx, cy in centers:
        verts = _hex_vertices(cx, cy, radius * 0.92)
        draw.line(verts + [verts[0]], fill=gold, width=max(2, int(3 * scale)))
        for vx, vy in verts:
            r = max(3, int(5 * scale))
            draw.ellipse((vx - r, vy - r, vx + r, vy + r), fill=(*GOLD, 150))

    extra = 10
    for _ in range(extra):
        ax, ay = rng.choice(centers)
        angle = rng.uniform(0, math.tau)
        length = radius * rng.uniform(1.6, 2.6)
        bx = ax + math.cos(angle) * length
        by = ay + math.sin(angle) * length
        draw.line((ax, ay, bx, by), fill=teal, width=max(2, int(2 * scale)))
        r = max(3, int(4 * scale))
        draw.ellipse((bx - r, by - r, bx + r, by + r), fill=(*TEAL, 140))

    return layer.filter(ImageFilter.GaussianBlur(radius=0.4))


def paste_overlay(base: Image.Image, overlay: Image.Image) -> Image.Image:
    if base.mode != "RGBA":
        merged = base.convert("RGBA")
    else:
        merged = base.copy()
    merged.alpha_composite(overlay)
    return merged.convert("RGB")


def brand_mark(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float) -> None:
    """Gold hex molecule inside a ring — used as the TrueHold mark."""
    outer = _hex_vertices(cx, cy, radius)
    inner = _hex_vertices(cx, cy, radius * 0.46)
    draw.line(outer + [outer[0]], fill=GOLD, width=max(4, int(radius / 18)))
    draw.line(inner + [inner[0]], fill=TEAL, width=max(3, int(radius / 24)))
    for (ax, ay), (bx, by) in zip(outer, inner):
        draw.line((ax, ay, bx, by), fill=GOLD_SOFT, width=max(2, int(radius / 28)))
    node = max(4, int(radius / 12))
    for vx, vy in (*outer, *inner, (cx, cy)):
        draw.ellipse((vx - node, vy - node, vx + node, vy + node), fill=GOLD)


def gold_bars(draw: ImageDraw.ImageDraw, size: tuple[int, int], thickness: int = 16) -> None:
    width, height = size
    draw.rectangle((0, 0, width, thickness), fill=GOLD)
    draw.rectangle((0, height - thickness, width, height), fill=GOLD)


LOGO_JPEG = ASSETS / "logo.jpeg"
LOGO_PATH = ASSETS / "logo.jpg"
HERO_PATH = ASSETS / "hero.jpg"
SERVICE_PATH = ASSETS / "service.jpg"


def official_logo() -> Path | None:
    if LOGO_JPEG.is_file():
        return LOGO_JPEG
    if LOGO_PATH.is_file():
        return LOGO_PATH
    return None


def paste_logo(image: Image.Image, *, box: int = 140, margin: int = 48) -> None:
    path = official_logo()
    if path is None:
        return
    logo = Image.open(path).convert("RGB")
    logo.thumbnail((box, box))
    image.paste(logo, (image.size[0] - logo.size[0] - margin, margin))
