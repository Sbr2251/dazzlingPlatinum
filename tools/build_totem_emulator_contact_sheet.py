#!/usr/bin/env python3
"""Build a deterministic nearest-neighbor contact sheet from isolated Totem emulator proofs."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPTURE_ROOT = (
    ROOT
    / "deliverables/totem-overworld-sprites/emulator-runtime-billboard-species-proofs"
)
DEFAULT_OUTPUT = DEFAULT_CAPTURE_ROOT / "totem-native-proof-contact-sheet.png"
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

# Fixed crop around the east-adjacent runtime-injected object at Route 206.
CROP_BOX = (96, 48, 152, 112)
SCALE = 5
LABEL_HEIGHT = 26
COLUMNS = 2
ROWS = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    capture_root = args.capture_root.resolve()
    output = args.output.resolve()

    font = ImageFont.load_default()
    cell_width = (CROP_BOX[2] - CROP_BOX[0]) * SCALE
    cell_image_height = (CROP_BOX[3] - CROP_BOX[1]) * SCALE
    cell_height = LABEL_HEIGHT + cell_image_height
    sheet = Image.new(
        "RGB",
        (cell_width * COLUMNS, cell_height * ROWS),
        "#20242a",
    )
    draw = ImageDraw.Draw(sheet)

    for index, species in enumerate(SPECIES):
        source = capture_root / species / "00_gallery_loaded.png"
        frame = Image.open(source).convert("RGB")
        crop = frame.crop(CROP_BOX).resize(
            (cell_width, cell_image_height),
            Image.Resampling.NEAREST,
        )
        column = index % COLUMNS
        row = index // COLUMNS
        x = column * cell_width
        y = row * cell_height
        sheet.paste(crop, (x, y + LABEL_HEIGHT))
        draw.rectangle(
            (x, y, x + cell_width - 1, y + LABEL_HEIGHT - 1),
            fill="#20242a",
        )
        draw.text((x + 8, y + 8), species.title(), fill="white", font=font)
        draw.rectangle(
            (x, y, x + cell_width - 1, y + cell_height - 1),
            outline="#707780",
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    print(output)


if __name__ == "__main__":
    main()
