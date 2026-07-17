#!/usr/bin/env python3
"""Inspect and decode simple Nintendo DS BMD0/BTX0 TEX0 sections.

This project-owned utility implements only the documented Nitro container,
TEX0, information-block, and indexed-texture formats required to inspect
Platinum's field build-model and overworld texture archives. It does not
execute or depend on third-party code.
"""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class InfoBlock:
    count: int
    datum_size: int
    data: list[bytes]
    names: list[str]


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def read_name(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("ascii", errors="replace")


def parse_info_block(data: bytes, off: int) -> InfoBlock:
    dummy = data[off]
    count = data[off + 1]
    if dummy != 0:
        raise ValueError(f"info block at {off:#x}: dummy={dummy}, expected 0")
    cursor = off + 12 + 4 * count
    datum_size = u16(data, cursor)
    data_section_size = u16(data, cursor + 2)
    cursor += 4
    entries = [data[cursor + i * datum_size : cursor + (i + 1) * datum_size] for i in range(count)]
    cursor += count * datum_size
    names = [read_name(data[cursor + i * 16 : cursor + (i + 1) * 16]) for i in range(count)]
    expected_min = 12 + 4 * count + 4 + count * datum_size + count * 16
    if data_section_size and data_section_size < count * datum_size:
        raise ValueError(
            f"info block at {off:#x}: data section {data_section_size} smaller than entries"
        )
    if off + expected_min > len(data):
        raise ValueError(f"info block at {off:#x} extends beyond file")
    return InfoBlock(count=count, datum_size=datum_size, data=entries, names=names)


def tex_format_byte_length(fmt: int, width: int, height: int) -> int:
    texels = width * height
    bits_per_texel = {1: 8, 2: 2, 3: 4, 4: 8, 5: 2, 6: 8, 7: 16}.get(fmt)
    if bits_per_texel is None:
        raise ValueError(f"unsupported texture format {fmt}")
    return texels * bits_per_texel // 8


def rgb555_to_rgba(value: int, alpha: int = 255) -> tuple[int, int, int, int]:
    r5 = value & 0x1F
    g5 = (value >> 5) & 0x1F
    b5 = (value >> 10) & 0x1F
    return ((r5 << 3) | (r5 >> 2), (g5 << 3) | (g5 >> 2), (b5 << 3) | (b5 >> 2), alpha)


def decode_indexed(
    texture_data: bytes,
    palette_data: bytes,
    width: int,
    height: int,
    fmt: int,
    transparent_zero: bool,
) -> Image.Image:
    colors = [rgb555_to_rgba(u16(palette_data, i)) for i in range(0, len(palette_data) - 1, 2)]
    indexes: list[int] = []
    if fmt == 2:
        for byte in texture_data:
            indexes.extend(((byte >> 0) & 3, (byte >> 2) & 3, (byte >> 4) & 3, (byte >> 6) & 3))
    elif fmt == 3:
        for byte in texture_data:
            indexes.extend((byte & 0xF, byte >> 4))
    elif fmt == 4:
        indexes.extend(texture_data)
    else:
        raise ValueError(f"decoder supports indexed formats 2, 3, and 4; found {fmt}")

    rgba: list[tuple[int, int, int, int]] = []
    for index in indexes[: width * height]:
        if index >= len(colors):
            color = (255, 0, 255, 255)
        else:
            color = colors[index]
        if index == 0 and transparent_zero:
            color = (color[0], color[1], color[2], 0)
        rgba.append(color)
    image = Image.new("RGBA", (width, height))
    image.putdata(rgba)
    return image


def parse_bmd(path: Path, output_dir: Path | None) -> dict[str, Any]:
    data = path.read_bytes()
    if data[:4] not in (b"BMD0", b"BTX0"):
        raise ValueError(f"{path}: not a BMD0 or BTX0 container")
    if u16(data, 4) != 0xFEFF:
        raise ValueError(f"{path}: unexpected BOM")
    file_size = u32(data, 8)
    header_size = u16(data, 12)
    section_count = u16(data, 14)
    section_offsets = [u32(data, 16 + i * 4) for i in range(section_count)]
    section_stamps = [data[off : off + 4].decode("ascii", errors="replace") for off in section_offsets]
    result: dict[str, Any] = {
        "path": str(path),
        "container": data[:4].decode("ascii"),
        "actual_size": len(data),
        "header_file_size": file_size,
        "header_size": header_size,
        "section_count": section_count,
        "sections": [
            {"offset": off, "stamp": stamp, "size": u32(data, off + 4)}
            for off, stamp in zip(section_offsets, section_stamps)
        ],
        "textures": [],
        "palettes": [],
    }

    tex_offsets = [off for off, stamp in zip(section_offsets, section_stamps) if stamp == "TEX0"]
    if not tex_offsets:
        return result
    tex0 = tex_offsets[0]
    # Layout follows Nitro TEX0 as documented by the audited 0BSD reference.
    tex_block_len = u16(data, tex0 + 12) << 3
    texture_info_rel = u16(data, tex0 + 14)
    tex_block_rel = u32(data, tex0 + 20)
    compressed_block_len = u16(data, tex0 + 28) << 3
    compressed_info_rel = u16(data, tex0 + 30)
    compressed1_rel = u32(data, tex0 + 36)
    compressed2_rel = u32(data, tex0 + 40)
    pal_block_len = u16(data, tex0 + 48) << 3
    palette_info_rel = u32(data, tex0 + 52)
    pal_block_rel = u32(data, tex0 + 56)

    tex_info = parse_info_block(data, tex0 + texture_info_rel)
    pal_info = parse_info_block(data, tex0 + palette_info_rel)
    pal_block = data[tex0 + pal_block_rel : tex0 + pal_block_rel + pal_block_len]

    palettes: list[dict[str, Any]] = []
    for name, entry in zip(pal_info.names, pal_info.data):
        if len(entry) != 4:
            raise ValueError(f"palette {name}: expected 4-byte datum, found {len(entry)}")
        offset = u16(entry, 0) << 3
        palettes.append({"name": name, "offset": offset})
    for i, palette in enumerate(palettes):
        next_offset = palettes[i + 1]["offset"] if i + 1 < len(palettes) else pal_block_len
        palette["byte_length"] = max(0, next_offset - palette["offset"])
        palette["color_capacity"] = palette["byte_length"] // 2
    result["palettes"] = palettes

    textures: list[dict[str, Any]] = []
    for index, (name, entry) in enumerate(zip(tex_info.names, tex_info.data)):
        if len(entry) != 8:
            raise ValueError(f"texture {name}: expected 8-byte datum, found {len(entry)}")
        params = u32(entry, 0)
        offset = (params & 0xFFFF) << 3
        width = 8 << ((params >> 20) & 0x7)
        height = 8 << ((params >> 23) & 0x7)
        fmt = (params >> 26) & 0x7
        transparent_zero = bool((params >> 29) & 1)
        byte_length = tex_format_byte_length(fmt, width, height)
        texture = {
            "index": index,
            "name": name,
            "params": f"0x{params:08X}",
            "offset": offset,
            "width": width,
            "height": height,
            "format": fmt,
            "transparent_zero": transparent_zero,
            "byte_length": byte_length,
            "data_file_offset": tex0 + tex_block_rel + offset if fmt != 5 else tex0 + compressed1_rel + offset,
        }
        textures.append(texture)
    result["textures"] = textures
    result["tex0"] = {
        "offset": tex0,
        "texture_info_offset": tex0 + texture_info_rel,
        "texture_block_offset": tex0 + tex_block_rel,
        "texture_block_length": tex_block_len,
        "compressed_info_offset": tex0 + compressed_info_rel,
        "compressed_block_length": compressed_block_len,
        "compressed1_offset": tex0 + compressed1_rel,
        "compressed2_offset": tex0 + compressed2_rel,
        "palette_info_offset": tex0 + palette_info_rel,
        "palette_block_offset": tex0 + pal_block_rel,
        "palette_block_length": pal_block_len,
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for texture in textures:
            if texture["format"] not in (2, 3, 4):
                continue
            start = texture["data_file_offset"]
            raw = data[start : start + texture["byte_length"]]
            for palette_index, palette in enumerate(palettes):
                pal_start = palette["offset"]
                pal_end = pal_start + palette["byte_length"]
                image = decode_indexed(
                    raw,
                    pal_block[pal_start:pal_end],
                    texture["width"],
                    texture["height"],
                    texture["format"],
                    texture["transparent_zero"],
                )
                safe_texture = texture["name"] or f"texture_{texture['index']}"
                safe_palette = palette["name"] or f"palette_{palette_index}"
                image.save(output_dir / f"{safe_texture}__{safe_palette}.png")

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    all_results: list[dict[str, Any]] = []
    for path in args.inputs:
        destination = args.output_dir / path.stem if args.output_dir else None
        result = parse_bmd(path, destination)
        all_results.append(result)
        print(
            f"{path.name}: sections={[s['stamp'] for s in result['sections']]} "
            f"textures={len(result['textures'])} palettes={len(result['palettes'])}"
        )
        for texture in result["textures"]:
            print(
                f"  texture {texture['name']!r}: {texture['width']}x{texture['height']} "
                f"fmt={texture['format']} bytes={texture['byte_length']} "
                f"transparent0={texture['transparent_zero']}"
            )
        for palette in result["palettes"]:
            print(
                f"  palette {palette['name']!r}: off={palette['offset']} "
                f"bytes={palette['byte_length']} colors={palette['color_capacity']}"
            )
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(all_results, indent=2) + "\n")


if __name__ == "__main__":
    main()
