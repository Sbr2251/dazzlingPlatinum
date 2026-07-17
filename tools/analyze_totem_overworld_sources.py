#!/usr/bin/env python3
"""Analyze and preview sourced Totem overworld sheets.

Expected input format is six 32x32 frames laid out horizontally: two down,
two up, and two side-facing frames. The script reports image mode, palette
usage, per-frame nontransparent bounds, and writes a native-pixel contact
sheet plus an enlarged nearest-neighbor review sheet.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


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

FRAME_LABELS = ("down_a", "down_b", "up_a", "up_b", "side_a", "side_b")


def alpha_bbox(frame: Image.Image) -> tuple[int, int, int, int] | None:
    rgba = frame.convert("RGBA")
    alpha = rgba.getchannel("A")
    return alpha.getbbox()


def visible_colors(frame: Image.Image) -> set[tuple[int, int, int, int]]:
    return {pixel for pixel in frame.convert("RGBA").getdata() if pixel[3] != 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []

    native = Image.new("RGBA", (6 * 32, len(SPECIES) * 48), (245, 245, 245, 255))
    draw = ImageDraw.Draw(native)

    for row, species in enumerate(SPECIES):
        path = args.input_dir / f"{species}.png"
        image = Image.open(path)
        if image.size != (192, 32):
            raise ValueError(f"{path}: expected 192x32, found {image.size}")

        rgba = image.convert("RGBA")
        frame_records: list[dict[str, object]] = []
        for index, label in enumerate(FRAME_LABELS):
            frame = rgba.crop((index * 32, 0, (index + 1) * 32, 32))
            bbox = alpha_bbox(frame)
            frame_records.append(
                {
                    "label": label,
                    "bbox": list(bbox) if bbox else None,
                    "visible_pixels": sum(1 for pixel in frame.getdata() if pixel[3] != 0),
                    "visible_colors": len(visible_colors(frame)),
                }
            )
            native.alpha_composite(frame, (index * 32, row * 48 + 16))

        source_visible_colors = visible_colors(rgba)
        records.append(
            {
                "species": species,
                "path": str(path),
                "mode": image.mode,
                "size": list(image.size),
                "visible_color_count": len(source_visible_colors),
                "frames": frame_records,
            }
        )
        draw.rectangle((0, row * 48, native.width - 1, row * 48 + 47), outline=(190, 190, 190, 255))
        draw.text((2, row * 48 + 2), species.upper(), fill=(20, 20, 20, 255))

    native_path = args.output_dir / "source-sheets-native-contact.png"
    native.save(native_path)
    enlarged = native.resize((native.width * 4, native.height * 4), Image.Resampling.NEAREST)
    enlarged_path = args.output_dir / "source-sheets-4x-contact.png"
    enlarged.save(enlarged_path)

    report = {
        "frame_layout": list(FRAME_LABELS),
        "records": records,
        "native_contact_sheet": str(native_path),
        "enlarged_contact_sheet": str(enlarged_path),
    }
    (args.output_dir / "source-sheet-analysis.json").write_text(json.dumps(report, indent=2) + "\n")

    for record in records:
        print(
            f"{record['species']}: mode={record['mode']} "
            f"visible_colors={record['visible_color_count']}"
        )
    print(native_path)
    print(enlarged_path)


if __name__ == "__main__":
    main()
