#!/usr/bin/env python3
"""Inject indexed PNG frames into a Platinum BMD0 or BTX0 TEX0 container.

The Totem overworld pipeline uses this project-owned utility to clone one of
Platinum's two-frame static-Pokémon BTX0 members, replace both 32x32 format-3
textures, and replace its shared 16-color palette. It relies only on the
container offsets parsed by ``inspect_nitro_bmd_textures.py`` and never runs
third-party conversion code.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PIL import Image

import inspect_nitro_bmd_textures as nitro_parser


def rgba_to_rgb555(r: int, g: int, b: int) -> int:
    """Convert 8-bit RGB to the Nintendo DS 15-bit BGR555 layout."""
    return ((r >> 3) & 0x1F) | (((g >> 3) & 0x1F) << 5) | (((b >> 3) & 0x1F) << 10)


def load_indexed_frame(path: Path) -> tuple[int, int, bytes, bytes]:
    """Return width, height, format-3 texels, and a 16-entry DS palette."""
    with Image.open(path) as image:
        if image.mode != "P":
            raise ValueError(f"{path}: expected an indexed (P) PNG")
        width, height = image.size
        palette = image.getpalette()
        if palette is None:
            raise ValueError(f"{path}: indexed image has no palette")
        pixels = list(image.getdata())

    if width * height % 2:
        raise ValueError(f"{path}: pixel count must be even for format-3 packing")
    if any(pixel > 15 for pixel in pixels):
        raise ValueError(f"{path}: uses a palette index above 15")

    texels = bytearray(width * height // 2)
    for index in range(0, len(pixels), 2):
        texels[index // 2] = pixels[index] | (pixels[index + 1] << 4)

    ds_palette = bytearray(32)
    for index in range(1, 16):
        base = index * 3
        if base + 2 < len(palette):
            color = rgba_to_rgb555(palette[base], palette[base + 1], palette[base + 2])
            struct.pack_into("<H", ds_palette, index * 2, color)

    return width, height, bytes(texels), bytes(ds_palette)


def inject_frames(template_path: Path, frame_paths: list[Path], output_path: Path) -> None:
    """Clone ``template_path`` and replace its leading textures and shared palette."""
    if not frame_paths:
        raise ValueError("At least one frame is required")

    container = nitro_parser.parse_bmd(template_path, None)
    textures = container.get("textures", [])
    palettes = container.get("palettes", [])
    if len(textures) < len(frame_paths):
        raise ValueError(
            f"{template_path}: has {len(textures)} textures but {len(frame_paths)} frames were supplied"
        )
    if len(palettes) != 1:
        raise ValueError(f"{template_path}: expected exactly one shared palette, found {len(palettes)}")

    encoded_frames = [load_indexed_frame(path) for path in frame_paths]
    reference_palette = encoded_frames[0][3]
    for path, encoded in zip(frame_paths[1:], encoded_frames[1:]):
        if encoded[3] != reference_palette:
            raise ValueError(f"{path}: palette differs from the first frame")

    data = bytearray(template_path.read_bytes())
    for path, target, encoded in zip(frame_paths, textures, encoded_frames):
        width, height, texels, _ = encoded
        if target["format"] != 3:
            raise ValueError(f"{template_path}: texture {target['name']} is not format 3")
        if (target["width"], target["height"]) != (width, height):
            raise ValueError(
                f"{path}: {width}x{height} does not match target {target['width']}x{target['height']}"
            )
        if len(texels) != target["byte_length"]:
            raise ValueError(
                f"{path}: packed size {len(texels)} does not match target {target['byte_length']}"
            )
        start = target["data_file_offset"]
        data[start : start + len(texels)] = texels

    palette = palettes[0]
    if palette["byte_length"] < len(reference_palette):
        raise ValueError(f"{template_path}: palette block is smaller than 16 colors")
    palette_start = container["tex0"]["palette_block_offset"] + palette["offset"]
    data[palette_start : palette_start + len(reference_palette)] = reference_palette

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    frame_names = ", ".join(path.name for path in frame_paths)
    print(
        f"Injected {len(frame_paths)} frame(s) [{frame_names}] into "
        f"{container['container']} template {template_path.name} -> {output_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True, help="Template BMD0 or BTX0 container")
    parser.add_argument(
        "--frame",
        type=Path,
        action="append",
        required=True,
        help="Indexed PNG frame; repeat in target texture order",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output BMD0 or BTX0 path")
    args = parser.parse_args()
    inject_frames(args.template, args.frame, args.output)


if __name__ == "__main__":
    main()
