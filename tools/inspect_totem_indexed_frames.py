#!/usr/bin/env python3
"""Report transparency/index invariants for prepared Totem overworld frames."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image


SPECIES = (
    "hitmonlee",
    "vespiquen",
    "skarmory",
    "lapras",
    "spiritomb",
    "aggron",
    "mamoswine",
    "kingdra",
)


def inspect_frame(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        pixels = list(image.getdata())
        rgba = image.convert("RGBA")
        alpha = [pixel[3] for pixel in rgba.getdata()]
        corners = [
            image.getpixel((0, 0)),
            image.getpixel((image.width - 1, 0)),
            image.getpixel((0, image.height - 1)),
            image.getpixel((image.width - 1, image.height - 1)),
        ]
        return {
            "path": str(path),
            "mode": image.mode,
            "size": list(image.size),
            "png_transparency": image.info.get("transparency"),
            "corner_indices": corners,
            "index_histogram": dict(sorted(Counter(pixels).items())),
            "transparent_alpha_pixels": sum(value == 0 for value in alpha),
            "opaque_alpha_pixels": sum(value == 255 for value in alpha),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    records = []
    for species in SPECIES:
        for suffix in ("idle_a", "idle_b"):
            records.append(inspect_frame(args.input_dir / f"{species}_{suffix}.png"))

    report = {"records": records}
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
