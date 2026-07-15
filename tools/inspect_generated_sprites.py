#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
from PIL import Image

FILES = [
    "research/mega-sinnoh-starters/generated/mega_torterra_front_concept.png",
    "research/mega-sinnoh-starters/generated/mega_torterra_back_refined.png",
    "research/mega-sinnoh-starters/generated/mega_infernape_front_refined.png",
    "research/mega-sinnoh-starters/generated/mega_infernape_back_concept.png",
    "research/mega-sinnoh-starters/generated/mega_empoleon_front_concept.png",
    "research/mega-sinnoh-starters/generated/mega_empoleon_back_concept.png",
]

for filename in FILES:
    path = Path(filename)
    image = Image.open(path).convert("RGBA")
    rgba = list(image.getdata())
    alpha = Counter(pixel[3] for pixel in rgba)
    colors = Counter(pixel[:3] for pixel in rgba)
    width, height = image.size
    border = []
    border.extend(image.crop((0, 0, width, 1)).getdata())
    border.extend(image.crop((0, height - 1, width, height)).getdata())
    border.extend(image.crop((0, 0, 1, height)).getdata())
    border.extend(image.crop((width - 1, 0, width, height)).getdata())
    border_colors = Counter(pixel[:3] for pixel in border)
    print(f"{path.name}: size={image.size} mode={Image.open(path).mode}")
    print(f"  alpha={alpha.most_common(6)}")
    print(f"  colors={colors.most_common(10)}")
    print(f"  border={border_colors.most_common(10)}")
