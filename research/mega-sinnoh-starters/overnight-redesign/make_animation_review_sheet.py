#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

SPECIES = ("torterra", "infernape", "empoleon")
VIEWS = ("front", "back")
BG = (88, 104, 120, 255)


def panel(source: Path, species: str, view: str) -> Image.Image:
    f0 = Image.open(source / species / f"{view}_f0.png").convert("RGBA")
    f1 = Image.open(source / species / f"{view}_f1.png").convert("RGBA")
    scale = 5
    label_h = 28
    gap = 12
    width = 80 * scale * 2 + gap + 24
    height = label_h + 80 * scale + 16
    out = Image.new("RGB", (width, height), (31, 35, 43))
    draw = ImageDraw.Draw(out)
    draw.text((12, 7), f"{species} {view}: frame 0 | frame 1", fill=(245, 245, 245))
    for i, frame in enumerate((f0, f1)):
        tile = Image.new("RGBA", (80, 80), BG)
        tile.alpha_composite(frame)
        large = tile.resize((80 * scale, 80 * scale), Image.Resampling.NEAREST).convert("RGB")
        out.paste(large, (12 + i * (80 * scale + gap), label_h))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    panels = [panel(args.source, species, view) for species in SPECIES for view in VIEWS]
    sheet = Image.new("RGB", (panels[0].width * 2, panels[0].height * 3), (20, 22, 27))
    for i, item in enumerate(panels):
        sheet.paste(item, ((i % 2) * item.width, (i // 2) * item.height))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)


if __name__ == "__main__":
    main()
