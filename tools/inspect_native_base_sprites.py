#!/usr/bin/env python3
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "res/pokemon/torterra/male_front.png",
    ROOT / "res/pokemon/torterra/male_back.png",
    ROOT / "res/pokemon/infernape/male_front.png",
    ROOT / "res/pokemon/infernape/male_back.png",
    ROOT / "res/pokemon/empoleon/male_front.png",
    ROOT / "res/pokemon/empoleon/male_back.png",
]


def rgba_bbox(frame: Image.Image):
    rgba = frame.convert("RGBA")
    alpha = rgba.getchannel("A")
    return alpha.getbbox()


def visible_colors(frame: Image.Image):
    rgba = frame.convert("RGBA")
    counts = rgba.getcolors(maxcolors=1_000_000) or []
    values = [(count, color) for count, color in counts if color[3] > 0]
    return sorted(values, reverse=True)


for path in FILES:
    image = Image.open(path)
    print(path.relative_to(ROOT), image.mode, image.size)
    for idx in range(2):
        frame = image.crop((80 * idx, 0, 80 * (idx + 1), 80))
        print(f"  frame {idx}: bbox={rgba_bbox(frame)}")
    colors = visible_colors(image)
    print(f"  visible colors={len(colors)}")
    print("  palette=" + ", ".join(f"#{r:02X}{g:02X}{b:02X}:{count}" for count, (r, g, b, _a) in colors))
