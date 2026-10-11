#!/usr/bin/env python3
"""Textures and palettes for the Solaceon memorial wall, appended to overworld texture set 010.

Usage:
  python3 tools/solaceon_town/textures.py                 dry run: what would be added, VRAM before/after
  python3 tools/solaceon_town/textures.py --write         write res/field/maps/texture_sets/map_texture_set_010.nsbtx
  python3 tools/solaceon_town/textures.py --preview DIR   PNG previews

Set 010 belongs to area 0xA: Solaceon Town, Celestic Town, Routes 209, 210 North/South, 211 East and 215. APPEND-ONLY:
stock textures and palettes keep their names and data, so those maps don't change. Rebuilt from BASE_REV (idempotent).

New texel data (one 1024 B strip, procedural pixel art, deterministic):
  sol_wall   128x16 pltt16: eight 16x16 cells, five used, one per sign event of s-celestic's wall (x 556, z 652..656):
             0 photo cards (z 652), 1 a child's drawing of a man and a Ponyta (653), 2 a lone card, ELIAS (654),
             3 the violet Team Eclipse banner WHO DID YOU LOSE? (655), 4 a new card, a smiling boy, a shiny pin (656)
New palette only:
  sol_stone  for blueglay (paving) -> the warm grey memorial stone of the wall body
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402
import nsbtx  # noqa: E402

BASE_REV = "065698b277"      # arc2 before world-art: stock set 010 and chunk 072
SET_REL = "res/field/maps/texture_sets/map_texture_set_010.nsbtx"

RECOLOURS = [
    ("sol_stone", "blueglay", "blueglay", [(78, 72, 70), (122, 114, 108), (162, 154, 144), (196, 188, 176)], ()),
]

PAL = [(58, 44, 36), (86, 66, 52), (240, 240, 232), (176, 170, 160), (40, 36, 44), (120, 176, 232), (96, 168, 88),
       (240, 196, 160), (110, 70, 40), (210, 48, 48), (240, 140, 40), (250, 214, 80), (246, 230, 200), (92, 52, 132),
       (220, 226, 240), (176, 140, 210)]
BOARD, BOARD2, WHITE, GREY, INK, SKY, GREEN, SKIN, HAIR, RED, ORANGE, YELLOW, CREAM, VIOLET, SILVER, LILAC = range(16)
CELL = 16
NCELLS = 8


def board(rng):
    c = [[BOARD] * CELL for _ in range(CELL)]
    for y in range(CELL):
        for x in range(CELL):
            if rng.random() < 0.18:
                c[y][x] = BOARD2
    return c


def rect(c, x0, y0, w, h, v):
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            if 0 <= x < CELL and 0 <= y < CELL:
                c[y][x] = v


def card(c, x0, y0, w, h, rng, kind):
    """A photo card: white border, a little picture inside, shadow on the right/bottom, a red pin at the top."""
    rect(c, x0 + 1, y0 + 1, w, h, INK)                       # shadow
    rect(c, x0, y0, w, h, WHITE)
    if kind == "photo":
        rect(c, x0 + 1, y0 + 1, w - 2, (h - 2) // 2, SKY)
        rect(c, x0 + 1, y0 + 1 + (h - 2) // 2, w - 2, h - 2 - (h - 2) // 2, rng.choice((GREEN, SKIN, CREAM)))
        cx = x0 + w // 2
        c[y0 + h // 2][cx] = rng.choice((HAIR, INK, ORANGE))   # a figure
    elif kind == "text":
        for k in range(1, h - 1, 2):
            rect(c, x0 + 1, y0 + k, w - 2 - (k % 3), 1, INK)
    c[y0][x0 + w // 2] = RED                                  # pin


def cell_photos(rng):
    c = board(rng)
    for (x, y, w, h) in ((1, 1, 6, 5), (8, 1, 6, 6), (1, 7, 5, 6), (7, 8, 6, 5), (10, 13, 5, 3), (2, 13, 6, 3)):
        card(c, x, y, w, h, rng, "photo" if (x + y) % 3 else "text")
    return c


def cell_ponyta(rng):
    c = board(rng)
    rect(c, 2, 2, 13, 12, INK)
    rect(c, 1, 1, 13, 12, WHITE)                              # paper
    # Ponyta: cream body, legs, orange/yellow flame mane and tail
    rect(c, 6, 6, 5, 3, CREAM)
    for x in (6, 7, 9, 10):
        rect(c, x, 9, 1, 2, INK)
    rect(c, 10, 4, 2, 3, CREAM)                               # neck + head
    c[4][12] = CREAM
    for (x, y) in ((9, 3), (10, 2), (9, 4), (8, 5), (11, 3)):
        c[y][x] = ORANGE
    for (x, y) in ((10, 3), (9, 2), (8, 4)):
        c[y][x] = YELLOW
    for (x, y) in ((5, 6), (4, 5), (4, 7)):
        c[y][x] = ORANGE
    # the man: a stick figure
    c[4][3] = SKIN
    rect(c, 3, 5, 1, 4, INK)
    c[6][2] = INK
    c[6][4] = INK
    c[9][2] = INK
    c[9][4] = INK
    rect(c, 1, 11, 13, 1, GREEN)                              # crayon grass
    c[1][7] = RED
    return c


def cell_elias(rng):
    c = board(rng)
    card(c, 3, 4, 10, 8, rng, "text")
    rect(c, 4, 6, 6, 1, INK)                                  # the name, bolder
    return c


def cell_banner(rng):
    c = board(rng)
    rect(c, 0, 2, CELL, 11, VIOLET)
    rect(c, 0, 12, CELL, 1, INK)                              # hem shadow
    for x in range(0, CELL, 3):
        c[13][x] = VIOLET                                     # fringe
    # the eclipse mark: a ring
    for (x, y) in ((2, 5), (3, 4), (4, 5), (3, 6), (2, 6), (4, 6), (2, 4), (4, 4)):
        c[y][x] = LILAC
    c[5][3] = INK
    # two rows of pale glyphs
    for row, y in ((0, 4), (1, 8)):
        x = 6 if row == 0 else 2
        while x < CELL - 1:
            n = rng.choice((1, 2))
            rect(c, x, y, n, 2, LILAC if rng.random() < 0.8 else SILVER)
            x += n + 1
    c[2][1] = SILVER
    c[2][CELL - 2] = SILVER
    return c


def cell_teo(rng):
    c = board(rng)
    rect(c, 3, 3, 11, 11, INK)
    rect(c, 2, 2, 11, 11, WHITE)
    rect(c, 3, 3, 9, 7, SKY)
    # the boy: hair, face, a smile
    rect(c, 5, 4, 5, 2, HAIR)
    rect(c, 5, 6, 5, 4, SKIN)
    c[7][6] = INK
    c[7][8] = INK
    rect(c, 6, 9, 3, 1, RED)
    rect(c, 3, 10, 9, 0, WHITE)
    rect(c, 4, 11, 7, 1, INK)                                 # the name line
    c[2][7] = SILVER                                          # the shiny pin
    c[1][7] = SILVER
    c[2][8] = WHITE
    return c


def cell_spare(rng):
    return board(rng)


def make_strip():
    rng = random.Random(2016)
    cells = [cell_photos(rng), cell_ponyta(rng), cell_elias(rng), cell_banner(rng), cell_teo(rng)]
    cells += [cell_spare(rng) for _ in range(NCELLS - len(cells))]
    return [[cells[x // CELL][y][x % CELL] for x in range(CELL * NCELLS)] for y in range(CELL)]


def entries():
    t, p = C.indexed_texture("sol_wall", make_strip(), PAL, c0=0)
    return [t], [p]


MATERIALS = {
    "sol_wall": ("sol_wall", "sol_wall_pl", (128, 16)),
    "sol_stone": ("blueglay", "sol_stone", (16, 16)),
}
CELL_ORDER = ["photos", "ponyta", "elias", "banner", "teo"]   # z 652..656


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
