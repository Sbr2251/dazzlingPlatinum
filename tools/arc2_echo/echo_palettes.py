#!/usr/bin/env python3
"""Arc 2 echo (S8): print the ghost palettes for the Resonator echoes (src/field_move_tasks.c, sEchoGhostPalettes).

Each overworld sprite's palette is read from the built mmodel NARC (the member comes from the gfx -> mmodel table
Unk_ov5_021FB484 in src/overlay005/ov5_021FAF40.c) and washed the way the Resonator cut-in washes a totem's front
sprite (FieldMoves_ApplyResonatorGhostPalette): each colour keeps its brightness but turns pale violet, the darkest
shades lifted to indigo. Colour 0 is transparent and kept.

    python3 tools/arc2_echo/echo_palettes.py [build/res/prebuilt/data/mmodel/mmodel.narc]
"""
import os
import re
import struct
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GFX = [
    "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M",
    "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F",
    "OBJ_EVENT_GFX_ECLIPSE_CRATE",
    "OBJ_EVENT_GFX_SHARD_FRAME",
    "OBJ_EVENT_GFX_RIFT_ARC2",
    "OBJ_EVENT_GFX_TOTEM_HITMONLEE",
    "OBJ_EVENT_GFX_TOTEM_SKARMORY",
    "OBJ_EVENT_GFX_PIKACHU",  # the Plusle and Minun stand-in
]


def narc_members(path):
    d = open(path, "rb").read()
    assert d[:4] == b"NARC"
    o = struct.unpack_from("<H", d, 0xC)[0]
    assert d[o:o + 4] == b"BTAF"
    size, count = struct.unpack_from("<IH", d, o + 4)
    fat = [struct.unpack_from("<II", d, o + 12 + 8 * i) for i in range(count)]
    o2 = o + size
    o3 = o2 + struct.unpack_from("<I", d, o2 + 4)[0]
    assert d[o3:o3 + 4] == b"GMIF"
    base = o3 + 8
    return [d[base + s:base + e] for s, e in fat]


def first_palette(btx):
    assert btx[:4] == b"BTX0"
    tex = btx[struct.unpack_from("<I", btx, 0x10)[0]:]
    assert tex[:4] == b"TEX0"
    size = struct.unpack_from("<H", tex, 0x30)[0] << 3
    data = struct.unpack_from("<I", tex, 0x38)[0]
    assert size >= 32
    return list(struct.unpack_from("<16H", tex, data))


def wash(colors):
    out = [colors[0]]
    for c in colors[1:]:
        r, g, b = c & 0x1F, (c >> 5) & 0x1F, (c >> 10) & 0x1F
        luma = (r * 77 + g * 151 + b * 28) >> 8
        r = min(31, 8 + (luma * 20) // 31)
        g = min(31, 6 + (luma * 20) // 31)
        b = min(31, 15 + (luma * 16) // 31)
        out.append((c & 0x8000) | r | (g << 5) | (b << 10))
    return out


def mmodel_members():
    src = open(os.path.join(REPO, "src/overlay005/ov5_021FAF40.c")).read()
    table = src[src.index("Unk_ov5_021FC9B4[] = {"):]
    table = table[:table.index("};")]
    return {m.group(1): int(m.group(2), 0) for m in re.finditer(r"\{\s*(OBJ_EVENT_GFX_\w+),\s*(0x[0-9A-Fa-f]+|\d+)\s*\}", table)}


def main():
    narc = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "build/res/prebuilt/data/mmodel/mmodel.narc")
    members = narc_members(narc)
    table = mmodel_members()
    for gfx in GFX:
        pal = wash(first_palette(members[table[gfx]]))
        print("    { %s," % gfx)
        print("        { " + ", ".join("0x%04X" % c for c in pal[:8]) + ",")
        print("          " + ", ".join("0x%04X" % c for c in pal[8:]) + " } },")


if __name__ == "__main__":
    main()
