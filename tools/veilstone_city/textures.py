#!/usr/bin/env python3
"""Textures and palettes for the Veilstone Meteor Shrine, appended to overworld texture set 011.

Usage:
  python3 tools/veilstone_city/textures.py                 dry run: what would be added, VRAM before/after
  python3 tools/veilstone_city/textures.py --write         write res/field/maps/texture_sets/map_texture_set_011.nsbtx
  python3 tools/veilstone_city/textures.py --preview DIR   PNG previews

Set 011 belongs to area 0xB, which only Veilstone City uses among the overworld headers (the other two area-0xB
headers, UNKNOWN_276/277, have no map cells). APPEND-ONLY, rebuilt from BASE_REV (idempotent).

New texel data (64 B, procedural):
  vs_shide    8x16 pltt16, colour 0 transparent: a zigzag paper streamer (shide) hung from the shrine ropes
New palettes only (stock texels, recoloured by luminance):
  vs_red      for c07_criff  (bordered panel)  -> vermilion: torii posts and beams
  vs_black    for c07_criff                    -> black lacquer: the torii's top cap
  vs_wood     for c07_criff                    -> dark wood: the rope posts
  vs_straw    for nbridge    (twisted planks)  -> straw: the shimenawa ropes
  vs_glow     for c07_base_x (lit window)      -> warm lamplight in grey stone: the lanterns' fire boxes (explicit
              colours per index, not a luminance ramp)
The lantern stone is stock c07_criff with its stock palette.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402
import nsbtx  # noqa: E402

BASE_REV = "065698b277"      # arc2 before world-art: stock set 011 and chunk 080
SET_REL = "res/field/maps/texture_sets/map_texture_set_011.nsbtx"

RECOLOURS = [
    ("vs_red", "c07_criff", "c07_criff_pl", [(110, 22, 16), (200, 52, 30), (226, 84, 48)], ()),
    ("vs_black", "c07_criff", "c07_criff_pl", [(30, 26, 28), (60, 54, 56), (84, 76, 78)], ()),
    ("vs_wood", "c07_criff", "c07_criff_pl", [(46, 30, 20), (88, 60, 38), (112, 80, 52)], ()),
    ("vs_straw", "nbridge", "dun_bridge", [(104, 82, 36), (158, 128, 62), (206, 180, 104), (236, 216, 146)], (0,)),
]
# c07_base_x indices: 0 the window, 1 its frame, 2..4 the stone around it (by row): lamplight in a stone box
GLOW_PAL = [(255, 236, 150), (214, 150, 60), (92, 86, 80), (120, 114, 106), (150, 144, 136)]

SHIDE_PAL = [(0, 0, 0), (246, 246, 240), (196, 196, 188)]


def make_shide():
    """8x16: a white paper strip folded in a zigzag (three steps down), a grey fold shadow."""
    g = [[0] * 8 for _ in range(16)]
    for y in range(16):
        step = min(3, y // 4)
        x0 = 1 + (step % 2) * 3
        for x in range(x0, x0 + 4):
            g[y][x] = 2 if y % 4 == 3 else 1
    return g


def entries():
    t, p = C.indexed_texture("vs_shide", make_shide(), SHIDE_PAL)
    glow = dict(name="vs_glow", colors=[nsbtx.bgr555(c) for c in GLOW_PAL] + [0] * 11, pltt4=0)
    return [t], [p, glow]


MATERIALS = {
    "vs_red": ("c07_criff", "vs_red", (16, 16)),
    "vs_black": ("c07_criff", "vs_black", (16, 16)),
    "vs_wood": ("c07_criff", "vs_wood", (16, 16)),
    "vs_straw": ("nbridge", "vs_straw", (32, 32)),
    "vs_glow": ("c07_base_x", "vs_glow", (16, 16)),
    "vs_shide": ("vs_shide", "vs_shide_pl", (8, 16)),
    "vs_stone": ("c07_criff", "c07_criff_pl", (16, 16)),
}
STRAW_V = (20 / 32, 28 / 32)       # the twisted strip of nbridge (rows 20..27)


def build_set():
    tex, pals = entries()
    return C.texset_append(SET_REL, BASE_REV, RECOLOURS, tex, pals)


def preview(out_bytes, d):
    import png
    os.makedirs(d, exist_ok=True)
    s = nsbtx.parse(out_bytes)
    T = {t["name"]: t for t in s["textures"]}
    P = {p["name"]: p for p in s["palettes"]}
    for name, (tn, pn, _) in MATERIALS.items():
        rows, _ = nsbtx.decode(T[tn], P[pn]["colors"])
        png.write_rgba(os.path.join(d, f"{name}.png"), T[tn]["w"], T[tn]["h"], [[tuple(p) for p in r] for r in rows])


def main():
    base, out, rep = build_set()
    print(rep)
    if "--preview" in sys.argv:
        preview(out, sys.argv[sys.argv.index("--preview") + 1])
    if "--write" in sys.argv:
        open(os.path.join(ROOT, SET_REL), "wb").write(out)
        print("wrote", SET_REL, len(out), "B")


if __name__ == "__main__":
    main()
