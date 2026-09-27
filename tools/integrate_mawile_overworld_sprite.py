#!/usr/bin/env python3
"""Integrate the Mawile overworld sprite (OBJ_EVENT_GFX_MAWILE) into Platinum.

The integration is append-only, following tools/integrate_totem_overworld_sprites.py:
existing object graphics IDs and mmodel members keep their numbers, the new
graphics constant is appended to generated/object_events_gfx.txt and the new
texture is mmodel member 478.

Unlike the Totems (two idle frames), Mawile has to walk, face and jump in all
four directions, so its member clones the layout of a stock 16-frame Pokemon
walker (Skitty, mmodel member 77, graphics ID OBJ_EVENT_GFX_SKITTY) and uses
the same renderer, animation and draw-table rows as Skitty.

The art lives in ONE file, res/field/objects/mawile/mawile_overworld.png. The
member is generated from it at build time (see the custom_target in
res/prebuilt/data/mmodel/mmodel/meson.build), so swapping the art is: replace
that PNG and run `make release`. This script has no third-party dependencies
(no PIL) because the build runs it with the system Python.

Sheet format (see docs/arc1/mawile_sprite.md):
  * indexed-colour PNG (bit depth 4 or 8), non-interlaced;
  * every pixel uses palette index 0-15; index 0 is transparent;
  * 32x32 cells, one row per facing direction in the order
    up (back view), down (front view), left, right;
  * 4 columns (128x128): stand, step A, stand, step B  -> used as-is;
    2 columns (64x128):  stand, step                   -> expanded to
    stand, step, stand, step (HGSS-style two-frame walk cycles).

Subcommands:
  integrate           (default) idempotently register the constant, the
                      overlay 5 table rows and the meson custom_target.
  build-member        write the BTX0 member from the sheet (used by meson).
  extract-placeholder rewrite the sheet from the stock template (Skitty).
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

CONSTANT = "OBJ_EVENT_GFX_MAWILE"
MEMBER = 478
MEMBER_FILENAME = f"mmodel_{MEMBER:08d}.bin"

TEMPLATE_SPECIES = "skitty"
TEMPLATE_CONSTANT = "OBJ_EVENT_GFX_SKITTY"
TEMPLATE_MEMBER = 0x4D
TEMPLATE_FILENAME = f"mmodel_{TEMPLATE_MEMBER:08d}.bin"

SHEET_RELPATH = Path("res/field/objects/mawile/mawile_overworld.png")
MMODEL_DIR_RELPATH = Path("res/prebuilt/data/mmodel/mmodel")
TOOL_RELPATH = Path("tools/integrate_mawile_overworld_sprite.py")

CELL = 32
DIRECTIONS = ("up", "down", "left", "right")
FRAMES_PER_DIRECTION = 4
FRAME_COUNT = len(DIRECTIONS) * FRAMES_PER_DIRECTION

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# Minimal indexed PNG reader/writer
# ---------------------------------------------------------------------------


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_indexed_png(path: Path) -> tuple[int, int, list[int], list[tuple[int, int, int]]]:
    """Return width, height, row-major palette indexes and the RGB palette."""
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"{path}: not a PNG file")

    pos = len(PNG_SIGNATURE)
    header = None
    palette: list[tuple[int, int, int]] = []
    idat = bytearray()
    while pos < len(data):
        length, kind = struct.unpack_from(">I4s", data, pos)
        body = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            palette = [tuple(body[i : i + 3]) for i in range(0, len(body), 3)]
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break

    if header is None:
        raise ValueError(f"{path}: missing IHDR")
    width, height, depth, color_type, _, _, interlace = header
    if color_type != 3:
        raise ValueError(f"{path}: must be an indexed-colour PNG (colour type 3), found type {color_type}")
    if depth not in (1, 2, 4, 8):
        raise ValueError(f"{path}: unsupported bit depth {depth}")
    if interlace:
        raise ValueError(f"{path}: interlaced PNGs are not supported")
    if not palette:
        raise ValueError(f"{path}: missing PLTE palette")

    raw = zlib.decompress(bytes(idat))
    stride = (width * depth + 7) // 8
    bpp = 1
    previous = bytearray(stride)
    pixels: list[int] = []
    offset = 0
    mask = (1 << depth) - 1
    for _ in range(height):
        filter_type = raw[offset]
        line = bytearray(raw[offset + 1 : offset + 1 + stride])
        offset += 1 + stride
        for i in range(stride):
            left = line[i - bpp] if i >= bpp else 0
            up = previous[i]
            up_left = previous[i - bpp] if i >= bpp else 0
            if filter_type == 1:
                line[i] = (line[i] + left) & 0xFF
            elif filter_type == 2:
                line[i] = (line[i] + up) & 0xFF
            elif filter_type == 3:
                line[i] = (line[i] + ((left + up) >> 1)) & 0xFF
            elif filter_type == 4:
                line[i] = (line[i] + _paeth(left, up, up_left)) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"{path}: bad PNG filter {filter_type}")
        for x in range(width):
            bit = x * depth
            byte = line[bit >> 3]
            shift = 8 - depth - (bit & 7)
            pixels.append((byte >> shift) & mask)
        previous = line

    return width, height, pixels, palette


def write_indexed_png(
    path: Path, width: int, height: int, pixels: list[int], palette: list[tuple[int, int, int]]
) -> None:
    """Write a 4-bit indexed PNG with a 16-colour palette."""
    if len(palette) != 16:
        raise ValueError("expected a 16-colour palette")
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        row = pixels[y * width : (y + 1) * width]
        for x in range(0, width, 2):
            rows.append((row[x] << 4) | (row[x + 1] if x + 1 < width else 0))

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    png = PNG_SIGNATURE
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 4, 3, 0, 0, 0))
    png += chunk(b"PLTE", b"".join(bytes(color) for color in palette))
    png += chunk(b"tRNS", b"\x00")  # index 0 is transparent in game; show it that way in editors
    png += chunk(b"IDAT", zlib.compress(bytes(rows), 9))
    png += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


# ---------------------------------------------------------------------------
# Minimal BTX0 / TEX0 access (same layout as inspect_nitro_bmd_textures.py)
# ---------------------------------------------------------------------------


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _info_block(data: bytes, off: int) -> tuple[list[bytes], list[str]]:
    count = data[off + 1]
    cursor = off + 12 + 4 * count
    datum_size = _u16(data, cursor)
    cursor += 4
    entries = [data[cursor + i * datum_size : cursor + (i + 1) * datum_size] for i in range(count)]
    cursor += count * datum_size
    names = [data[cursor + i * 16 : cursor + (i + 1) * 16].split(b"\0", 1)[0].decode("ascii") for i in range(count)]
    return entries, names


def parse_btx0(data: bytes) -> tuple[dict[int, int], int]:
    """Return {frame number (1-16): texel file offset} and the palette file offset.

    Stock walker textures are named "<species>.<N>"; N is the frame number, so
    frames are addressed by name rather than by dictionary order.
    """
    if data[:4] != b"BTX0":
        raise ValueError("template is not a BTX0 container")
    tex0 = _u32(data, 16)
    if data[tex0 : tex0 + 4] != b"TEX0":
        raise ValueError("template has no TEX0 section")
    texture_info = tex0 + _u16(data, tex0 + 14)
    texture_block = tex0 + _u32(data, tex0 + 20)
    palette_info = tex0 + _u32(data, tex0 + 52)
    palette_block = tex0 + _u32(data, tex0 + 56)

    frames: dict[int, int] = {}
    entries, names = _info_block(data, texture_info)
    for name, entry in zip(names, entries):
        params = _u32(entry, 0)
        width = 8 << ((params >> 20) & 7)
        height = 8 << ((params >> 23) & 7)
        fmt = (params >> 26) & 7
        if (width, height, fmt) != (CELL, CELL, 3):
            raise ValueError(f"texture {name}: expected 32x32 format 3, found {width}x{height} format {fmt}")
        frames[int(name.rsplit(".", 1)[1])] = texture_block + ((params & 0xFFFF) << 3)
    if sorted(frames) != list(range(1, FRAME_COUNT + 1)):
        raise ValueError(f"template must have textures .1-.{FRAME_COUNT}, found {sorted(frames)}")

    pal_entries, _ = _info_block(data, palette_info)
    if len(pal_entries) != 1:
        raise ValueError(f"template must have one palette, found {len(pal_entries)}")
    return frames, palette_block + (_u16(pal_entries[0], 0) << 3)


def rgb_to_bgr555(color: tuple[int, int, int]) -> int:
    r, g, b = color
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def bgr555_to_rgb(value: int) -> tuple[int, int, int]:
    channels = (value & 0x1F, (value >> 5) & 0x1F, (value >> 10) & 0x1F)
    return tuple((c << 3) | (c >> 2) for c in channels)


# ---------------------------------------------------------------------------
# Sheet <-> frames
# ---------------------------------------------------------------------------


def load_sheet(path: Path) -> tuple[list[list[int]], list[tuple[int, int, int]]]:
    """Return 16 frames (each 1024 indexes, frame N at list index N-1) and the palette."""
    width, height, pixels, palette = read_indexed_png(path)
    if height != CELL * len(DIRECTIONS) or width not in (CELL * 2, CELL * 4):
        raise ValueError(
            f"{path}: sheet must be 128x128 (4 frames per direction) or 64x128 "
            f"(2 frames per direction), found {width}x{height}"
        )
    used = max(pixels)
    if used > 15:
        raise ValueError(f"{path}: uses palette index {used}; only indexes 0-15 are allowed")

    columns = width // CELL
    order = (0, 1, 2, 3) if columns == 4 else (0, 1, 0, 1)
    frames: list[list[int]] = []
    for row in range(len(DIRECTIONS)):
        for column in order:
            frame = []
            for y in range(CELL):
                start = (row * CELL + y) * width + column * CELL
                frame.extend(pixels[start : start + CELL])
            frames.append(frame)
    palette = (palette + [(0, 0, 0)] * 16)[:16]
    return frames, palette


def build_member(sheet: Path, template: Path, output: Path) -> None:
    frames, palette = load_sheet(sheet)
    data = bytearray(template.read_bytes())
    frame_offsets, palette_offset = parse_btx0(bytes(data))

    for number, frame in enumerate(frames, start=1):
        texels = bytes(frame[i] | (frame[i + 1] << 4) for i in range(0, len(frame), 2))
        start = frame_offsets[number]
        data[start : start + len(texels)] = texels

    ds_palette = bytearray(32)
    for index, color in enumerate(palette):
        struct.pack_into("<H", ds_palette, index * 2, rgb_to_bgr555(color))
    data[palette_offset : palette_offset + 32] = ds_palette

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


def extract_placeholder(template: Path, sheet: Path) -> None:
    data = template.read_bytes()
    frame_offsets, palette_offset = parse_btx0(data)
    palette = [bgr555_to_rgb(_u16(data, palette_offset + i * 2)) for i in range(16)]
    width, height = CELL * FRAMES_PER_DIRECTION, CELL * len(DIRECTIONS)
    pixels = [0] * (width * height)
    for number in range(1, FRAME_COUNT + 1):
        row, column = divmod(number - 1, FRAMES_PER_DIRECTION)
        raw = data[frame_offsets[number] : frame_offsets[number] + CELL * CELL // 2]
        for i, byte in enumerate(raw):
            for half, index in enumerate((byte & 0xF, byte >> 4)):
                x, y = (2 * i + half) % CELL, (2 * i + half) // CELL
                pixels[(row * CELL + y) * width + column * CELL + x] = index
    write_indexed_png(sheet, width, height, pixels, palette)


# ---------------------------------------------------------------------------
# Source registration (idempotent)
# ---------------------------------------------------------------------------


def insert_rows_before_sentinel(source: str, declaration: str, sentinel: str, rows: str) -> str:
    start = source.index(declaration)
    end = source.index(sentinel, start)
    if CONSTANT in source[start:end]:
        return source
    return source[:end] + rows + source[end:]


def update_object_graphics_list(path: Path) -> None:
    lines = path.read_text().rstrip().splitlines()
    if CONSTANT in lines:
        return
    if "OBJ_EVENT_GFX_TOTEM_KINGDRA" not in lines:
        raise ValueError(f"{path}: run tools/integrate_totem_overworld_sprites.py first")
    lines.append(CONSTANT)
    path.write_text("\n".join(lines) + "\n")


def gfx_id(path: Path, constant: str) -> int:
    return path.read_text().splitlines().index(constant)


def update_overlay_tables(path: Path, template_id: int) -> None:
    text = path.read_text()

    def template_row(declaration: str, pattern: str) -> str:
        """Copy the stock template's row so Mawile behaves exactly like it."""
        start = text.index(declaration)
        for candidate in (f"{{ 0x{template_id:X}, ", f"{{ 0x{template_id:x}, ", f"{{ {TEMPLATE_CONSTANT}, "):
            at = text.find(candidate, start)
            if at != -1 and text.find("};", start) > at:
                line_end = text.index("\n", at)
                return "    " + text[at:line_end].replace(candidate, f"{{ {CONSTANT}, ", 1) + "\n"
        raise ValueError(f"no {pattern} row for {TEMPLATE_CONSTANT} in {declaration}")

    tables = (
        ("const UnkStruct_ov5_021FB97C Unk_ov5_021FB97C[] = {", "    { 0xffff, NULL }", "renderer"),
        ("const UnkStruct_ov5_021EDD04 Unk_ov5_021FD77C[] = {", "    { 0xffff, 0xffff, 0xffff, NULL }", "animation"),
        ("const UnkStruct_ov5_021ECD10 Unk_ov5_021FC194[] = {", "    { 0xffff, 0x0, 0x0, 0x0, 0x0, 0x0 }", "draw"),
    )
    for declaration, sentinel, kind in tables:
        text = insert_rows_before_sentinel(text, declaration, sentinel, template_row(declaration, kind))

    text = insert_rows_before_sentinel(
        text,
        "const UnkStruct_ov5_021ED2D0 Unk_ov5_021FC9B4[] = {",
        "    { 0xffff, 0x0 }",
        f"    {{ {CONSTANT}, 0x{MEMBER:X} }},\n",
    )
    path.write_text(text)


MESON_MARKER = "# Mawile overworld sprite"
MESON_BLOCK = f"""
{MESON_MARKER} (OBJ_EVENT_GFX_MAWILE): generated at build time from
# {SHEET_RELPATH} by {TOOL_RELPATH}, cloning
# the stock {TEMPLATE_SPECIES.capitalize()} walker layout ({TEMPLATE_FILENAME}).
mmodel_files_targets += custom_target('{MEMBER_FILENAME}',
    output: '{MEMBER_FILENAME}',
    input: [
        meson.project_source_root() / '{SHEET_RELPATH}',
        '{TEMPLATE_FILENAME}',
    ],
    depend_files: meson.project_source_root() / '{TOOL_RELPATH}',
    command: [
        find_program(meson.project_source_root() / '{TOOL_RELPATH}', native: true),
        'build-member',
        '--sheet', '@INPUT0@',
        '--template', '@INPUT1@',
        '--output', '@OUTPUT@',
    ],
)
"""


def update_mmodel_meson(path: Path) -> None:
    text = path.read_text()
    if MESON_MARKER in text:
        return
    loop = text.find("    mmodel_files_targets += fs.copyfile(f)\n")
    loop_end = text.find("endforeach", loop)
    if loop == -1 or loop_end == -1:
        raise ValueError(f"{path}: copyfile loop not found")
    if f"'{MEMBER_FILENAME}'" in text:
        raise ValueError(f"{path}: {MEMBER_FILENAME} is already a prebuilt member")
    loop_end += len("endforeach")
    path.write_text(text[:loop_end].rstrip() + "\n" + MESON_BLOCK + text[loop_end:].lstrip("\n"))


def integrate(root: Path) -> None:
    gfx_list = root / "generated/object_events_gfx.txt"
    update_object_graphics_list(gfx_list)
    update_overlay_tables(root / "src/overlay005/ov5_021FAF40.c", gfx_id(gfx_list, TEMPLATE_CONSTANT))
    update_mmodel_meson(root / MMODEL_DIR_RELPATH / "meson.build")
    sheet = root / SHEET_RELPATH
    if not sheet.exists():
        extract_placeholder(root / MMODEL_DIR_RELPATH / TEMPLATE_FILENAME, sheet)
    # Validate the sheet now rather than at build time.
    load_sheet(sheet)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("integrate", help="register the sprite (default)")
    build = sub.add_parser("build-member", help="write the BTX0 member from the sheet")
    build.add_argument("--sheet", type=Path, required=True)
    build.add_argument("--template", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    extract = sub.add_parser("extract-placeholder", help="rewrite the sheet from the stock template")
    extract.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()

    try:
        if args.command == "build-member":
            build_member(args.sheet, args.template, args.output)
        elif args.command == "extract-placeholder":
            output = args.output or root / SHEET_RELPATH
            extract_placeholder(root / MMODEL_DIR_RELPATH / TEMPLATE_FILENAME, output)
            print(f"Wrote {TEMPLATE_SPECIES} placeholder sheet to {output}")
        else:
            integrate(root)
            print(f"Integrated {CONSTANT} (mmodel member {MEMBER}, template {TEMPLATE_SPECIES}).")
    except (ValueError, OSError) as error:
        print(f"{Path(__file__).name}: error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
