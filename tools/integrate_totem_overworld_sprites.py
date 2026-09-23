#!/usr/bin/env python3
"""Integrate eight Totem overworld billboard textures into Pokémon Platinum.

The integration is append-only: existing object graphics IDs and mmodel member
numbers are preserved. Each Totem clones Platinum's two-frame Uxie BTX0 layout,
uses tracked 32x32 indexed idle frames, and receives a new mmodel member from
470 through 477 plus a named object graphics constant.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from inject_nitro_bmd_textures import inject_frames


@dataclass(frozen=True)
class TotemSprite:
    species: str
    constant: str
    member: int

    @property
    def resource_hex(self) -> str:
        return f"0x{self.member:X}"

    @property
    def member_filename(self) -> str:
        return f"mmodel_{self.member:08d}.bin"


TOTEMS = (
    TotemSprite("hitmonlee", "OBJ_EVENT_GFX_TOTEM_HITMONLEE", 470),
    TotemSprite("vespiquen", "OBJ_EVENT_GFX_TOTEM_VESPIQUEN", 471),
    TotemSprite("skarmory", "OBJ_EVENT_GFX_TOTEM_SKARMORY", 472),
    TotemSprite("lapras", "OBJ_EVENT_GFX_TOTEM_LAPRAS", 473),
    TotemSprite("spiritomb", "OBJ_EVENT_GFX_TOTEM_SPIRITOMB", 474),
    TotemSprite("aggron", "OBJ_EVENT_GFX_TOTEM_AGGRON", 475),
    TotemSprite("mamoswine", "OBJ_EVENT_GFX_TOTEM_MAMOSWINE", 476),
    TotemSprite("kingdra", "OBJ_EVENT_GFX_TOTEM_KINGDRA", 477),
)


def insert_rows_before_sentinel(
    source: str,
    declaration: str,
    sentinel: str,
    rows: str,
    idempotence_marker: str,
) -> str:
    """Insert rows inside one named C array immediately before its sentinel."""
    start = source.index(declaration)
    end = source.index(sentinel, start)
    section = source[start:end]
    if idempotence_marker in section:
        return source
    return source[:end] + rows + source[end:]


def update_object_graphics_list(path: Path) -> None:
    text = path.read_text()
    if TOTEMS[0].constant in text:
        return

    lines = text.rstrip().splitlines()
    # The vanilla list stops at numeric ID 262 but reserves 263-275 in source
    # tables. Materialize those placeholders so the new names begin at 276 and
    # never collide with hard-coded numeric lookups already present in the ROM.
    for numeric_id in range(len(lines), 276):
        lines.append(f"OBJ_EVENT_GFX_UNK_{numeric_id}")
    lines.extend(totem.constant for totem in TOTEMS)
    path.write_text("\n".join(lines) + "\n")


def update_overlay_tables(path: Path) -> None:
    text = path.read_text()

    renderer_rows = "".join(
        f"    {{ {totem.constant}, &Unk_ov5_021FB0B4 }},\n" for totem in TOTEMS
    )
    text = insert_rows_before_sentinel(
        text,
        "const UnkStruct_ov5_021FB97C Unk_ov5_021FB97C[] = {",
        "    { 0xffff, NULL }",
        renderer_rows,
        TOTEMS[0].constant,
    )

    graphics_rows = "".join(
        f"    {{ {totem.constant}, {totem.resource_hex} }},\n" for totem in TOTEMS
    )
    text = insert_rows_before_sentinel(
        text,
        "const UnkStruct_ov5_021ED2D0 Unk_ov5_021FC9B4[] = {",
        "    { 0xffff, 0x0 }",
        graphics_rows,
        TOTEMS[0].constant,
    )

    animation_rows = "".join(
        f"    {{ {totem.constant}, 0x0, 0x8, Unk_ov5_021FB1C4 }},\n" for totem in TOTEMS
    )
    text = insert_rows_before_sentinel(
        text,
        "const UnkStruct_ov5_021EDD04 Unk_ov5_021FD77C[] = {",
        "    { 0xffff, 0xffff, 0xffff, NULL }",
        animation_rows,
        TOTEMS[0].constant,
    )

    draw_rows = "".join(
        f"    {{ {totem.constant}, 0x1, 0x1, 0x1, 0x1, 0x0 }},\n" for totem in TOTEMS
    )
    text = insert_rows_before_sentinel(
        text,
        "const UnkStruct_ov5_021ECD10 Unk_ov5_021FC194[] = {",
        "    { 0xffff, 0x0, 0x0, 0x0, 0x0, 0x0 }",
        draw_rows,
        TOTEMS[0].constant,
    )

    path.write_text(text)


def update_mmodel_build_list(path: Path) -> None:
    text = path.read_text()
    marker = TOTEMS[0].member_filename
    block_end_marker = "\n)\n\nmmodel_files_targets"
    block_end = text.index(block_end_marker)

    if marker not in text:
        prefix = text[:block_end].rstrip()
        if not prefix.endswith(","):
            prefix += ","
        rows = "".join(f"    '{totem.member_filename}',\n" for totem in TOTEMS)
        text = prefix + "\n" + rows + text[block_end:]

    # Also repair a list produced by the earliest development version, which
    # appended member 470 after vanilla member 469 without adding a comma.
    text = text.replace(
        "    'mmodel_00000469.bin'\n    'mmodel_00000470.bin',",
        "    'mmodel_00000469.bin',\n    'mmodel_00000470.bin',",
    )
    path.write_text(text)


def generate_btx0_members(root: Path) -> None:
    template = root / "res/prebuilt/data/mmodel/mmodel/mmodel_00000130.bin"
    source_dir = root / "res/field/objects/totems"
    output_dir = root / "res/prebuilt/data/mmodel/mmodel"

    if not template.exists():
        raise FileNotFoundError(template)

    for totem in TOTEMS:
        frames = [
            source_dir / f"{totem.species}_idle_a.png",
            source_dir / f"{totem.species}_idle_b.png",
        ]
        missing = [str(frame) for frame in frames if not frame.exists()]
        if missing:
            raise FileNotFoundError(", ".join(missing))
        inject_frames(template, frames, output_dir / totem.member_filename)


def integrate(root: Path) -> None:
    update_object_graphics_list(root / "generated/object_events_gfx.txt")
    update_overlay_tables(root / "src/overlay005/ov5_021FAF40.c")
    update_mmodel_build_list(root / "res/prebuilt/data/mmodel/mmodel/meson.build")
    generate_btx0_members(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root",
    )
    args = parser.parse_args()
    integrate(args.root.resolve())
    print("Integrated eight Totem overworld sprites (members 470-477).")


if __name__ == "__main__":
    main()
