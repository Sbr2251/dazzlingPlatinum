#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image, ImageDraw

WORK = Path("/home/ubuntu/dazzlingPlatinum/research/mega-sinnoh-starters/overnight-redesign")
DEFAULT_SOURCE = WORK / "target-native-v1"
SCALE = 8
MARGIN = 30
BG = (88, 104, 120, 255)


def grid_image(path: Path, label: str) -> Image.Image:
    src = Image.open(path).convert("RGBA")
    size = MARGIN * 2 + 80 * SCALE
    canvas = Image.new("RGBA", (size, size + 24), (32, 36, 44, 255))
    tile = Image.new("RGBA", (80, 80), BG)
    tile.alpha_composite(src)
    large = tile.resize((80 * SCALE, 80 * SCALE), Image.Resampling.NEAREST)
    canvas.alpha_composite(large, (MARGIN, MARGIN))
    draw = ImageDraw.Draw(canvas)
    for p in range(81):
        color = (10, 10, 10, 130) if p % 5 else (235, 235, 235, 150)
        x = MARGIN + p * SCALE
        y = MARGIN + p * SCALE
        draw.line((x, MARGIN, x, MARGIN + 80 * SCALE), fill=color, width=1)
        draw.line((MARGIN, y, MARGIN + 80 * SCALE, y), fill=color, width=1)
    for p in range(0, 80, 10):
        draw.text((MARGIN + p * SCALE + 1, 10), str(p), fill="white")
        draw.text((2, MARGIN + p * SCALE + 1), str(p), fill="white")
    draw.text((MARGIN, size + 2), label, fill="white")
    return canvas.convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    source = args.source
    out = args.output or source / "pixel-grids"
    out.mkdir(parents=True, exist_ok=True)
    panels = []
    for species in ("torterra", "infernape", "empoleon"):
        for view in ("front", "back"):
            label = f"{species} {view}"
            panel = grid_image(source / species / f"{view}.png", label)
            panel.save(out / f"{species}_{view}_grid.png")
            panels.append(panel)
    sheet = Image.new("RGB", (panels[0].width * 2, panels[0].height * 3), (20, 20, 20))
    for i, panel in enumerate(panels):
        sheet.paste(panel, ((i % 2) * panel.width, (i // 2) * panel.height))
    sheet.save(out / "all_pixel_grids.png")


if __name__ == "__main__":
    main()
