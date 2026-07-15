#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research/mega-sinnoh-starters/native-grid-references"
OUT.mkdir(parents=True, exist_ok=True)

for species in ("torterra", "infernape", "empoleon"):
    for view in ("front", "back"):
        src = ROOT / f"res/pokemon/{species}/male_{view}.png"
        image = Image.open(src).convert("RGB")
        scale = 8
        enlarged = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
        canvas = Image.new("RGB", (enlarged.width, enlarged.height + 28), "white")
        canvas.paste(enlarged, (0, 28))
        draw = ImageDraw.Draw(canvas)
        for x in range(0, image.width + 1, 5):
            px = x * scale
            draw.line((px, 28, px, canvas.height - 1), fill=(180, 180, 180), width=1)
            if x % 10 == 0:
                draw.text((px + 2, 2), str(x), fill=(0, 0, 0))
        for y in range(0, image.height + 1, 5):
            py = 28 + y * scale
            draw.line((0, py, enlarged.width - 1, py), fill=(180, 180, 180), width=1)
            if y % 10 == 0:
                draw.text((2, max(28, py - 11)), str(y), fill=(0, 0, 0))
        draw.line((80 * scale, 28, 80 * scale, canvas.height - 1), fill=(255, 0, 255), width=3)
        canvas.save(OUT / f"{species}_{view}_grid.png")
