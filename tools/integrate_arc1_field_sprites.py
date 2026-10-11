#!/usr/bin/env python3
"""Register the Arc 1 field sprites and build their mmodel members from PNG sheets.

Arc 1 part 2 needs five new object graphics IDs. They are registered up front with
placeholder art (copies of stock sprites) so every workstream can reference the
constants from day 1; the Art stream later replaces the PNG sheets and nothing else.

| constant                               | member | layout  | placeholder copied from          |
|----------------------------------------|--------|---------|----------------------------------|
| OBJ_EVENT_GFX_SAROS                    | 479    | walker  | OBJ_EVENT_GFX_GENTLEMAN (0x22)   |
| OBJ_EVENT_GFX_ECLIPSE_GRUNT_M          | 480    | walker  | OBJ_EVENT_GFX_GRUNT_M (0x67)     |
| OBJ_EVENT_GFX_ECLIPSE_GRUNT_F          | 481    | walker  | OBJ_EVENT_GFX_GRUNT_F (0x68)     |
| OBJ_EVENT_GFX_ARC1_RIFT                | 482    | idle2   | OBJ_EVENT_GFX_ROCK_SMASH (0x53)  |
| OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET   | 483    | idle2   | OBJ_EVENT_GFX_TOTEM_HITMONLEE    |

Layouts (see docs/arc1/part2/sprites.md):
  walker  16 textures of 32x32 4bpp, cloned from the stock walker given above, with
          that walker's renderer/animation/draw rows (4 directions x stand, step A,
          stand, step B). Sheet: 128x128 (or 64x128, expanded to stand/step/stand/step),
          rows up, down, left, right.
  idle2   2 textures of 32x32 4bpp cloned from the Uxie member (mmodel 130) with the
          Totem rows (two-frame idle loop, no facing). Sheet: 64x32, frame A then B.

The integration is append-only like tools/integrate_mawile_overworld_sprite.py:
existing graphics IDs and mmodel members keep their numbers, the constants are
appended to generated/object_events_gfx.txt after OBJ_EVENT_GFX_MAWILE and the
members are generated at build time by meson custom_targets (no .bin checked in).
No third-party dependencies (no PIL): the build runs this with the system Python.

Subcommands:
  integrate            (default) idempotently register constants, overlay 5 rows and
                       the meson custom_targets; write any missing placeholder sheet;
                       validate every sheet.
  build-member         write one BTX0 member from its sheet (used by meson).
  extract-placeholder  rewrite one (or every) sheet from its stock placeholder source.
  check                validate every sheet without touching anything.
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from integrate_mawile_overworld_sprite import (  # noqa: E402
    _info_block,
    _u16,
    _u32,
    bgr555_to_rgb,
    read_indexed_png,
    rgb_to_bgr555,
    write_indexed_png,
)

CELL = 32
SHEET_DIR = Path("res/field/objects/arc1")
MMODEL_DIR = Path("res/prebuilt/data/mmodel/mmodel")
TOOL_RELPATH = Path("tools/integrate_arc1_field_sprites.py")
MAWILE_TOOL_RELPATH = Path("tools/integrate_mawile_overworld_sprite.py")
GFX_LIST = Path("generated/object_events_gfx.txt")
OVERLAY = Path("src/overlay005/ov5_021FAF40.c")
AFTER_CONSTANT = "OBJ_EVENT_GFX_MAWILE"

IDLE2_TEMPLATE_MEMBER = 130  # Uxie, the template every Totem member is cloned from


@dataclass(frozen=True)
class Sprite:
    constant: str
    member: int
    layout: str  # "walker" or "idle2"
    template_member: int  # BTX0 cloned for the output member
    rows_from: str  # stock constant whose overlay 5 rows are copied
    sheet_name: str
    placeholder: str  # how the placeholder sheet is made (see extract_placeholder)

    @property
    def sheet(self) -> Path:
        return SHEET_DIR / self.sheet_name

    @property
    def member_filename(self) -> str:
        return f"mmodel_{self.member:08d}.bin"

    @property
    def template_filename(self) -> str:
        return f"mmodel_{self.template_member:08d}.bin"

    @property
    def frame_count(self) -> int:
        return 16 if self.layout == "walker" else 2


SPRITES = (
    Sprite("OBJ_EVENT_GFX_SAROS", 479, "walker", 0x22, "OBJ_EVENT_GFX_GENTLEMAN", "saros.png", "template"),
    Sprite("OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", 480, "walker", 0x67, "OBJ_EVENT_GFX_GRUNT_M", "eclipse_grunt_m.png", "template"),
    Sprite("OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", 481, "walker", 0x68, "OBJ_EVENT_GFX_GRUNT_F", "eclipse_grunt_f.png", "template"),
    Sprite("OBJ_EVENT_GFX_ARC1_RIFT", 482, "idle2", IDLE2_TEMPLATE_MEMBER, "OBJ_EVENT_GFX_TOTEM_HITMONLEE", "arc1_rift.png", "breakrock"),
    Sprite("OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET", 483, "idle2", IDLE2_TEMPLATE_MEMBER, "OBJ_EVENT_GFX_TOTEM_HITMONLEE", "totem_hitmonlee_violet.png", "totem_hitmonlee"),
)

BY_CONSTANT = {s.constant: s for s in SPRITES}
BY_MEMBER_FILE = {s.member_filename: s for s in SPRITES}


# ---------------------------------------------------------------------------
# BTX0 access
# ---------------------------------------------------------------------------


def parse_btx0(data: bytes, frame_count: int) -> tuple[dict[int, int], int]:
    """Return {frame number (1-based): texel file offset} and the palette file offset.

    Textures are named "<name>.<N>"; N is the frame number.
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
    if sorted(frames) != list(range(1, frame_count + 1)):
        raise ValueError(f"template must have textures .1-.{frame_count}, found {sorted(frames)}")

    pal_entries, _ = _info_block(data, palette_info)
    if len(pal_entries) != 1:
        raise ValueError(f"template must have one palette, found {len(pal_entries)}")
    return frames, palette_block + (_u16(pal_entries[0], 0) << 3)


def first_texture(data: bytes) -> tuple[int, int, list[int], list[tuple[int, int, int]]]:
    """Width, height, indexes and palette of a single-texture 4bpp BTX0 (e.g. the Rock Smash rock)."""
    tex0 = _u32(data, 16)
    texture_info = tex0 + _u16(data, tex0 + 14)
    texture_block = tex0 + _u32(data, tex0 + 20)
    palette_info = tex0 + _u32(data, tex0 + 52)
    palette_block = tex0 + _u32(data, tex0 + 56)
    entries, _ = _info_block(data, texture_info)
    params = _u32(entries[0], 0)
    width = 8 << ((params >> 20) & 7)
    height = 8 << ((params >> 23) & 7)
    if (params >> 26) & 7 != 3:
        raise ValueError("placeholder texture is not 4bpp")
    start = texture_block + ((params & 0xFFFF) << 3)
    pixels = []
    for byte in data[start : start + width * height // 2]:
        pixels += [byte & 0xF, byte >> 4]
    pal_entries, _ = _info_block(data, palette_info)
    pal_off = palette_block + (_u16(pal_entries[0], 0) << 3)
    # Small stock textures may store fewer than 16 palette entries; pad with black.
    count = max(0, min(16, (len(data) - pal_off) // 2))
    palette = [bgr555_to_rgb(_u16(data, pal_off + 2 * i)) for i in range(count)]
    palette += [(0, 0, 0)] * (16 - count)
    if max(pixels) >= count:
        raise ValueError("placeholder texture uses a palette entry the file does not store")
    return width, height, pixels, palette


# ---------------------------------------------------------------------------
# Sheets
# ---------------------------------------------------------------------------


def load_sheet(sprite: Sprite, path: Path) -> tuple[list[list[int]], list[tuple[int, int, int]]]:
    """Return the member's frames (each CELL*CELL indexes, frame N at list index N-1) and the palette."""
    width, height, pixels, palette = read_indexed_png(path)
    if sprite.layout == "walker":
        if height != CELL * 4 or width not in (CELL * 2, CELL * 4):
            raise ValueError(f"{path}: walker sheet must be 128x128 or 64x128, found {width}x{height}")
        columns = width // CELL
        order = (0, 1, 2, 3) if columns == 4 else (0, 1, 0, 1)
        cells = [(row, column) for row in range(4) for column in order]
    else:
        if (width, height) != (CELL * 2, CELL):
            raise ValueError(f"{path}: idle sheet must be 64x32 (frame A, frame B), found {width}x{height}")
        cells = [(0, 0), (0, 1)]
    used = max(pixels)
    if used > 15:
        raise ValueError(f"{path}: uses palette index {used}; only indexes 0-15 are allowed")
    frames = []
    for row, column in cells:
        frame = []
        for y in range(CELL):
            start = (row * CELL + y) * width + column * CELL
            frame.extend(pixels[start : start + CELL])
        frames.append(frame)
    return frames, (palette + [(0, 0, 0)] * 16)[:16]


def build_member(sprite: Sprite, sheet: Path, template: Path, output: Path) -> None:
    frames, palette = load_sheet(sprite, sheet)
    data = bytearray(template.read_bytes())
    offsets, palette_offset = parse_btx0(bytes(data), sprite.frame_count)
    for number, frame in enumerate(frames, start=1):
        texels = bytes(frame[i] | (frame[i + 1] << 4) for i in range(0, len(frame), 2))
        data[offsets[number] : offsets[number] + len(texels)] = texels
    for index, color in enumerate(palette):
        struct.pack_into("<H", data, palette_offset + 2 * index, rgb_to_bgr555(color))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


def _frames_from_member(path: Path, frame_count: int):
    data = path.read_bytes()
    offsets, palette_offset = parse_btx0(data, frame_count)
    palette = [bgr555_to_rgb(_u16(data, palette_offset + 2 * i)) for i in range(16)]
    frames = []
    for number in range(1, frame_count + 1):
        frame = []
        for byte in data[offsets[number] : offsets[number] + CELL * CELL // 2]:
            frame += [byte & 0xF, byte >> 4]
        frames.append(frame)
    return frames, palette


def _write_sheet(sprite: Sprite, path: Path, frames: list[list[int]], palette) -> None:
    if sprite.layout == "walker":
        width, height, columns = CELL * 4, CELL * 4, 4
    else:
        width, height, columns = CELL * 2, CELL, 2
    pixels = [0] * (width * height)
    for number, frame in enumerate(frames):
        row, column = divmod(number, columns)
        for i, index in enumerate(frame):
            x, y = i % CELL, i // CELL
            pixels[(row * CELL + y) * width + column * CELL + x] = index
    write_indexed_png(path, width, height, pixels, list(palette))


def extract_placeholder(root: Path, sprite: Sprite, output: Path) -> None:
    mmodel = root / MMODEL_DIR
    if sprite.placeholder == "template":
        frames, palette = _frames_from_member(mmodel / sprite.template_filename, sprite.frame_count)
    elif sprite.placeholder == "totem_hitmonlee":
        frames = []
        palette = None
        for name in ("hitmonlee_idle_a.png", "hitmonlee_idle_b.png"):
            width, height, pixels, pal = read_indexed_png(root / "res/field/objects/totems" / name)
            if (width, height) != (CELL, CELL):
                raise ValueError(f"{name}: expected 32x32")
            frames.append(pixels)
            palette = palette or (pal + [(0, 0, 0)] * 16)[:16]
    elif sprite.placeholder == "breakrock":
        # The Rock Smash rock (OBJ_EVENT_GFX_ROCK_SMASH, member 0x53) is a single 16x16
        # texture; centre it horizontally and stand it on row 29 like stock 32x32 cells.
        width, height, pixels, palette = first_texture((mmodel / "mmodel_00000083.bin").read_bytes())
        frame = [0] * (CELL * CELL)
        ox, oy = (CELL - width) // 2, 30 - height
        for i, index in enumerate(pixels):
            frame[(oy + i // width) * CELL + ox + i % width] = index
        frames = [frame, list(frame)]
    else:
        raise ValueError(f"unknown placeholder kind {sprite.placeholder}")
    _write_sheet(sprite, output, frames, palette)


# ---------------------------------------------------------------------------
# Source registration (idempotent)
# ---------------------------------------------------------------------------


def update_object_graphics_list(path: Path) -> None:
    lines = path.read_text().rstrip().splitlines()
    if AFTER_CONSTANT not in lines:
        raise ValueError(f"{path}: {AFTER_CONSTANT} missing; run tools/integrate_mawile_overworld_sprite.py first")
    for sprite in SPRITES:
        if sprite.constant not in lines:
            lines.append(sprite.constant)
    path.write_text("\n".join(lines) + "\n")


def _template_row(text: str, declaration: str, template_id: int, template_constant: str, constant: str) -> str:
    start = text.index(declaration)
    end = text.index("};", start)
    for candidate in (f"{{ 0x{template_id:X}, ", f"{{ 0x{template_id:x}, ", f"{{ {template_constant}, "):
        at = text.find(candidate, start)
        if at != -1 and at < end:
            line_end = text.index("\n", at)
            return "    " + text[at:line_end].replace(candidate, f"{{ {constant}, ", 1) + "\n"
    raise ValueError(f"no row for {template_constant} in {declaration}")


def update_overlay_tables(path: Path, gfx_ids: dict[str, int]) -> None:
    text = path.read_text()
    tables = (
        ("const UnkStruct_ov5_021FB97C Unk_ov5_021FB97C[] = {", "    { 0xffff, NULL }"),
        ("const UnkStruct_ov5_021EDD04 Unk_ov5_021FD77C[] = {", "    { 0xffff, 0xffff, 0xffff, NULL }"),
        ("const UnkStruct_ov5_021ECD10 Unk_ov5_021FC194[] = {", "    { 0xffff, 0x0, 0x0, 0x0, 0x0, 0x0 }"),
        ("const UnkStruct_ov5_021ED2D0 Unk_ov5_021FC9B4[] = {", "    { 0xffff, 0x0 }"),
    )
    for declaration, sentinel in tables:
        for sprite in SPRITES:
            start = text.index(declaration)
            end = text.index(sentinel, start)
            if f"{{ {sprite.constant}, " in text[start:end]:
                continue
            if declaration.startswith("const UnkStruct_ov5_021ED2D0"):
                row = f"    {{ {sprite.constant}, 0x{sprite.member:X} }},\n"
            else:
                row = _template_row(text, declaration, gfx_ids[sprite.rows_from], sprite.rows_from, sprite.constant)
            text = text[:end] + row + text[end:]
    path.write_text(text)


MESON_MARKER = "# Arc 1 field sprites"


def meson_block() -> str:
    parts = [
        f"\n{MESON_MARKER} (OBJ_EVENT_GFX_SAROS, _ECLIPSE_GRUNT_M/_F, _ARC1_RIFT, _TOTEM_HITMONLEE_VIOLET):\n"
        f"# generated at build time from {SHEET_DIR}/*.png by {TOOL_RELPATH}.\n"
        "# Members must stay contiguous after 478 (narc create packs the directory in name order).\n"
    ]
    for sprite in SPRITES:
        parts.append(
            f"""mmodel_files_targets += custom_target('{sprite.member_filename}',
    output: '{sprite.member_filename}',
    input: [
        meson.project_source_root() / '{sprite.sheet}',
        '{sprite.template_filename}',
    ],
    depend_files: [
        meson.project_source_root() / '{TOOL_RELPATH}',
        meson.project_source_root() / '{MAWILE_TOOL_RELPATH}',
    ],
    command: [
        find_program(meson.project_source_root() / '{TOOL_RELPATH}', native: true),
        'build-member',
        '--constant', '{sprite.constant}',
        '--sheet', '@INPUT0@',
        '--template', '@INPUT1@',
        '--output', '@OUTPUT@',
    ],
)
"""
        )
    return "".join(parts)


def update_mmodel_meson(path: Path) -> None:
    text = path.read_text()
    if MESON_MARKER in text:
        return
    if "mmodel_00000478.bin" not in text:
        raise ValueError(f"{path}: Mawile member 478 missing; run tools/integrate_mawile_overworld_sprite.py first")
    path.write_text(text.rstrip("\n") + "\n" + meson_block())


def check(root: Path) -> None:
    for sprite in SPRITES:
        load_sheet(sprite, root / sprite.sheet)


def integrate(root: Path) -> None:
    gfx_list = root / GFX_LIST
    update_object_graphics_list(gfx_list)
    lines = gfx_list.read_text().splitlines()
    gfx_ids = {name: lines.index(name) for name in {s.rows_from for s in SPRITES}}
    update_overlay_tables(root / OVERLAY, gfx_ids)
    update_mmodel_meson(root / MMODEL_DIR / "meson.build")
    for sprite in SPRITES:
        if not (root / sprite.sheet).exists():
            extract_placeholder(root, sprite, root / sprite.sheet)
    check(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=TOOLS_DIR.parent, help="Repository root")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("integrate", help="register the sprites (default)")
    sub.add_parser("check", help="validate every sheet")
    build = sub.add_parser("build-member", help="write one BTX0 member from its sheet")
    build.add_argument("--constant", required=True, choices=sorted(BY_CONSTANT))
    build.add_argument("--sheet", type=Path, required=True)
    build.add_argument("--template", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    extract = sub.add_parser("extract-placeholder", help="rewrite sheet(s) from the stock placeholder source")
    extract.add_argument("--constant", choices=sorted(BY_CONSTANT), help="default: every sprite")
    extract.add_argument("--output", type=Path, help="only with --constant")
    args = parser.parse_args()
    root = args.root.resolve()

    try:
        if args.command == "build-member":
            build_member(BY_CONSTANT[args.constant], args.sheet, args.template, args.output)
        elif args.command == "extract-placeholder":
            targets = [BY_CONSTANT[args.constant]] if args.constant else list(SPRITES)
            for sprite in targets:
                output = args.output if (args.output and args.constant) else root / sprite.sheet
                extract_placeholder(root, sprite, output)
                print(f"Wrote placeholder sheet for {sprite.constant} to {output}")
        elif args.command == "check":
            check(root)
            print("All Arc 1 field sprite sheets are valid.")
        else:
            integrate(root)
            print("Integrated the Arc 1 field sprites (mmodel members 479-483).")
    except (ValueError, OSError) as error:
        print(f"{Path(__file__).name}: error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
