#!/usr/bin/env python3
"""Register the Arc 2 field sprites (placeholders) and build their mmodel members from PNG sheets.

Same mechanism as tools/integrate_arc1_field_sprites.py (docs/arc1/part2/sprites.md): the constants are appended to
generated/object_events_gfx.txt after OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET, overlay 5 gets one row per constant in
each of its four tables, and meson builds each member at build time from its sheet (no .bin checked in).

| constant                         | member | layout | placeholder copied from              |
|----------------------------------|--------|--------|--------------------------------------|
| OBJ_EVENT_GFX_INDRA              | 484    | walker | OBJ_EVENT_GFX_JUPITER (0x66)         |
| OBJ_EVENT_GFX_KAHN               | 485    | walker | OBJ_EVENT_GFX_SAILOR (0x36)          |
| OBJ_EVENT_GFX_LOOKER_JANITOR     | 486    | walker | OBJ_EVENT_GFX_LOOKER (0x178)         |
| OBJ_EVENT_GFX_LOOKER_NEWSPAPER   | 487    | walker | OBJ_EVENT_GFX_LOOKER (0x178)         |
| OBJ_EVENT_GFX_ECLIPSE_CRATE      | 488    | idle2  | the Rock Smash rock (member 0x53)    |
| OBJ_EVENT_GFX_SHARD_FRAME        | 489    | idle2  | the Rock Smash rock (member 0x53)    |
| OBJ_EVENT_GFX_RIFT_ARC2          | 490    | idle2  | the Rock Smash rock (member 0x53)    |

Sheets live in res/field/objects/arc2/ (art-ph replaces only those PNGs). Sheet rules: docs/arc1/part2/sprites.md.

Subcommands: integrate (default, idempotent), build-member (used by meson), extract-placeholder, check.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import integrate_arc1_field_sprites as arc1  # noqa: E402

SHEET_DIR = Path("res/field/objects/arc2")
TOOL_RELPATH = Path("tools/integrate_arc2_field_sprites.py")
ARC1_TOOL_RELPATH = Path("tools/integrate_arc1_field_sprites.py")
AFTER_CONSTANT = "OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET"
MESON_MARKER = "# Arc 2 field sprites"


@dataclass(frozen=True)
class Sprite(arc1.Sprite):
    @property
    def sheet(self) -> Path:
        return SHEET_DIR / self.sheet_name


IDLE2 = arc1.IDLE2_TEMPLATE_MEMBER
SPRITES = (
    Sprite("OBJ_EVENT_GFX_INDRA", 484, "walker", 0x66, "OBJ_EVENT_GFX_JUPITER", "indra.png", "template"),
    Sprite("OBJ_EVENT_GFX_KAHN", 485, "walker", 0x36, "OBJ_EVENT_GFX_SAILOR", "kahn.png", "template"),
    Sprite("OBJ_EVENT_GFX_LOOKER_JANITOR", 486, "walker", 0x178, "OBJ_EVENT_GFX_LOOKER", "looker_janitor.png", "template"),
    Sprite("OBJ_EVENT_GFX_LOOKER_NEWSPAPER", 487, "walker", 0x178, "OBJ_EVENT_GFX_LOOKER", "looker_newspaper.png", "template"),
    Sprite("OBJ_EVENT_GFX_ECLIPSE_CRATE", 488, "idle2", IDLE2, "OBJ_EVENT_GFX_TOTEM_HITMONLEE", "eclipse_crate.png", "breakrock"),
    Sprite("OBJ_EVENT_GFX_SHARD_FRAME", 489, "idle2", IDLE2, "OBJ_EVENT_GFX_TOTEM_HITMONLEE", "shard_frame.png", "breakrock"),
    Sprite("OBJ_EVENT_GFX_RIFT_ARC2", 490, "idle2", IDLE2, "OBJ_EVENT_GFX_TOTEM_HITMONLEE", "rift_arc2.png", "breakrock"),
)
BY_CONSTANT = {s.constant: s for s in SPRITES}


def update_object_graphics_list(path: Path) -> None:
    lines = path.read_text().rstrip().splitlines()
    if AFTER_CONSTANT not in lines:
        raise ValueError(f"{path}: {AFTER_CONSTANT} missing; run tools/integrate_arc1_field_sprites.py first")
    for sprite in SPRITES:
        if sprite.constant not in lines:
            lines.append(sprite.constant)
    path.write_text("\n".join(lines) + "\n")


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
                row = arc1._template_row(text, declaration, gfx_ids[sprite.rows_from], sprite.rows_from, sprite.constant)
            text = text[:end] + row + text[end:]
    path.write_text(text)


def meson_block() -> str:
    parts = [
        f"\n{MESON_MARKER} (OBJ_EVENT_GFX_INDRA, _KAHN, _LOOKER_JANITOR/_NEWSPAPER, _ECLIPSE_CRATE, _SHARD_FRAME,\n"
        f"# _RIFT_ARC2): generated at build time from {SHEET_DIR}/*.png by {TOOL_RELPATH}.\n"
        "# Members must stay contiguous after 483 (narc create packs the directory in name order).\n"
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
        meson.project_source_root() / '{ARC1_TOOL_RELPATH}',
        meson.project_source_root() / '{arc1.MAWILE_TOOL_RELPATH}',
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
    if "mmodel_00000483.bin" not in text:
        raise ValueError(f"{path}: Arc 1 member 483 missing; run tools/integrate_arc1_field_sprites.py first")
    path.write_text(text.rstrip("\n") + "\n" + meson_block())


def check(root: Path) -> None:
    for sprite in SPRITES:
        arc1.load_sheet(sprite, root / sprite.sheet)


def integrate(root: Path) -> None:
    gfx_list = root / arc1.GFX_LIST
    update_object_graphics_list(gfx_list)
    lines = gfx_list.read_text().splitlines()
    gfx_ids = {name: lines.index(name) for name in {s.rows_from for s in SPRITES}}
    update_overlay_tables(root / arc1.OVERLAY, gfx_ids)
    update_mmodel_meson(root / arc1.MMODEL_DIR / "meson.build")
    (root / SHEET_DIR).mkdir(parents=True, exist_ok=True)
    for sprite in SPRITES:
        if not (root / sprite.sheet).exists():
            arc1.extract_placeholder(root, sprite, root / sprite.sheet)
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
            arc1.build_member(BY_CONSTANT[args.constant], args.sheet, args.template, args.output)
        elif args.command == "extract-placeholder":
            targets = [BY_CONSTANT[args.constant]] if args.constant else list(SPRITES)
            for sprite in targets:
                output = args.output if (args.output and args.constant) else root / sprite.sheet
                arc1.extract_placeholder(root, sprite, output)
                print(f"Wrote placeholder sheet for {sprite.constant} to {output}")
        elif args.command == "check":
            check(root)
            print("All Arc 2 field sprite sheets are valid.")
        else:
            integrate(root)
            print("Integrated the Arc 2 field sprites (mmodel members 484-490).")
    except (ValueError, OSError) as error:
        print(f"{Path(__file__).name}: error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
