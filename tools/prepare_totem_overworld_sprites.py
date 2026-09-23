#!/usr/bin/env python3
"""Prepare six-frame Totem overworld sheets for Platinum BTX0 integration.

The sourced sheets use one uniform opaque corner color as a chroma background.
This tool removes that color, reserves indexed palette entry 0 for transparency,
quantizes only opaque sprite colors, and emits six 32x32 indexed frames. It can
also promote the two downward frames as the production idle pair.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


FRAME_NAMES = ("down_a", "down_b", "up_a", "up_b", "side_a", "side_b")
TRANSPARENT_RGB = (255, 0, 255)


def remove_uniform_corner_background(image: Image.Image) -> Image.Image:
    """Return RGBA pixels with a uniform four-corner chroma color made transparent."""
    rgba = image.convert("RGBA")
    corners = (
        rgba.getpixel((0, 0))[:3],
        rgba.getpixel((rgba.width - 1, 0))[:3],
        rgba.getpixel((0, rgba.height - 1))[:3],
        rgba.getpixel((rgba.width - 1, rgba.height - 1))[:3],
    )
    if len(set(corners)) != 1:
        return rgba

    chroma = corners[0]
    cleaned = []
    for red, green, blue, alpha in rgba.getdata():
        if (red, green, blue) == chroma:
            cleaned.append((red, green, blue, 0))
        else:
            cleaned.append((red, green, blue, alpha))
    rgba.putdata(cleaned)
    return rgba


def quantize_and_preserve_transparency(
    image: Image.Image,
    max_colors: int = 15,
) -> Image.Image:
    """Quantize opaque pixels while reserving indexed palette entry 0 for transparency."""
    rgba = remove_uniform_corner_background(image)
    opaque_colors = [pixel[:3] for pixel in rgba.getdata() if pixel[3] >= 128]
    if not opaque_colors:
        raise ValueError("Sprite sheet contains no opaque pixels")

    color_count = min(max_colors, len(set(opaque_colors)))
    sample = Image.new("RGB", (len(opaque_colors), 1))
    sample.putdata(opaque_colors)
    quantized = sample.quantize(
        colors=color_count,
        method=Image.Quantize.MAXCOVERAGE,
        dither=Image.Dither.NONE,
    )
    palette_bytes = quantized.getpalette()
    if palette_bytes is None:
        raise ValueError("Failed to obtain a palette from opaque sprite pixels")

    opaque_palette = [
        tuple(palette_bytes[index * 3 : index * 3 + 3])
        for index in range(color_count)
    ]
    new_palette = list(TRANSPARENT_RGB)
    for color in opaque_palette:
        new_palette.extend(color)
    new_palette.extend([0] * (768 - len(new_palette)))

    indexed = Image.new("P", rgba.size, color=0)
    indexed.putpalette(new_palette)
    indexed.info["transparency"] = 0

    nearest_cache: dict[tuple[int, int, int], int] = {}
    indexed_pixels: list[int] = []
    for red, green, blue, alpha in rgba.getdata():
        if alpha < 128:
            indexed_pixels.append(0)
            continue
        color = (red, green, blue)
        palette_index = nearest_cache.get(color)
        if palette_index is None:
            palette_index = min(
                range(1, color_count + 1),
                key=lambda index: sum(
                    (channel - opaque_palette[index - 1][offset]) ** 2
                    for offset, channel in enumerate(color)
                ),
            )
            nearest_cache[color] = palette_index
        indexed_pixels.append(palette_index)
    indexed.putdata(indexed_pixels)
    return indexed


def save_indexed_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, transparency=0, optimize=False)


def process_sheet(
    input_path: Path,
    output_dir: Path,
    idle_output_dir: Path | None,
) -> None:
    with Image.open(input_path) as source:
        if source.size != (192, 32):
            raise ValueError(
                f"Expected 192x32 image, got {source.size} for {input_path.name}"
            )
        quantized_sheet = quantize_and_preserve_transparency(source, max_colors=15)

    species = input_path.stem
    prepared_sheet_path = output_dir / f"{species}_prepared.png"
    save_indexed_png(quantized_sheet, prepared_sheet_path)

    for index, frame_name in enumerate(FRAME_NAMES):
        frame = quantized_sheet.crop((index * 32, 0, (index + 1) * 32, 32))
        frame.info["transparency"] = 0
        save_indexed_png(frame, output_dir / f"{species}_{frame_name}.png")
        if idle_output_dir is not None and index < 2:
            idle_name = "idle_a" if index == 0 else "idle_b"
            save_indexed_png(frame, idle_output_dir / f"{species}_{idle_name}.png")

    print(f"Prepared {species}: {prepared_sheet_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--idle-output-dir",
        type=Path,
        help="Optional production directory for downward idle_a/idle_b frames",
    )
    args = parser.parse_args()

    for path in sorted(args.input_dir.glob("*.png")):
        process_sheet(path, args.output_dir, args.idle_output_dir)


if __name__ == "__main__":
    main()
