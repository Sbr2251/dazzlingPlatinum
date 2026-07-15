#!/usr/bin/env python3
"""Inspect transparency and chroma-removal needs in revised Mega starter source sheets."""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/mega-sinnoh-starters/redesign/source"

for path in sorted(SOURCE.glob("mega_*_v[23].png")):
    image = Image.open(path).convert("RGBA")
    pixels = list(image.getdata())
    transparent = sum(a < 128 for _, _, _, a in pixels)
    magenta = sum(a >= 128 and r > 180 and b > 150 and g < 150 for r, g, b, a in pixels)
    green = sum(a >= 128 and g > 80 and g > r * 1.2 and g > b * 1.2 for r, g, b, a in pixels)
    near_black = sum(a >= 128 and max(r, g, b) < 12 for r, g, b, a in pixels)
    print(
        f"{path.name}: {image.width}x{image.height} "
        f"transparent={transparent / len(pixels):.1%} magenta={magenta / len(pixels):.1%} "
        f"green={green / len(pixels):.1%} near_black={near_black / len(pixels):.1%} "
        f"corners={[image.getpixel(point) for point in [(0,0),(image.width-1,0),(0,image.height-1),(image.width-1,image.height-1)]]}"
    )
