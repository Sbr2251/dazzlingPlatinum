#!/usr/bin/env python3
"""Paints the six raid field sprites (raid_maps.md section 2, "New field sprites") as 16-colour idle2 sheets.
Standard library only (tools/lake_verity/png.py).

    python3 tools/solaceon_ruins/sprites.py                 # dry run: builds every sheet, runs the checks
    python3 tools/solaceon_ruins/sprites.py --preview DIR   # also writes <name>_x8.png contact sheets to DIR
    python3 tools/solaceon_ruins/sprites.py --write         # writes res/graphics/field_sprites/objects/<name>.png

The mac tree's field sprites are 32x64 sheets: frame A in rows 0-31, frame B in rows 32-63 (nitrobtx --spritesheet
--num-frames 2, see res/graphics/field_sprites/meson.build). Sheet rules (docs/arc1/part2/sprites.md): 16 colours,
index 0 transparent, centred on x=15, the lowest pixel on row 29.

| constant                            | how it is made                                                              |
|-------------------------------------|-----------------------------------------------------------------------------|
| OBJ_EVENT_GFX_SHARD_GENERATOR       | painted: gunmetal cabinet on skids, violet shard window (pulses A/B), amber lamp, vented top with a black-sun ring stencil, black and violet cables |
| OBJ_EVENT_GFX_SHARD_GENERATOR_OFF   | the same drawing, window dark glass, lamp off, violet cable grey; A = B      |
| OBJ_EVENT_GFX_SHARD_BARRIER         | painted curtain of violet light, rows 12-30 only (never hides who stands behind it), dithered holes, a moving band; period 16 px so neighbouring tiles' curtains overlap into one wall |
| OBJ_EVENT_GFX_SHARD_FRAME_DARK      | palette swap of res/graphics/field_sprites/objects/shard_frame.png: the violet ramp to stone greys; A = B (a drained rack doesn't twinkle) |
| OBJ_EVENT_GFX_VIOLET_CRYSTAL_DARK   | palette swap of violet_crystal.png the same way; A = B                       |
| OBJ_EVENT_GFX_DIG_ROPE              | painted: two wooden posts, a sagging rope with red and white flags and a little brass bell that swings |
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import png  # noqa: E402

OBJ_DIR = os.path.join(ROOT, "res", "graphics", "field_sprites", "objects")
CELL = 32
FEET = 29
MAGENTA = (255, 0, 255)


class Frame:
    def __init__(self):
        self.px = [[0] * CELL for _ in range(CELL)]

    def set(self, x, y, v):
        if 0 <= x < CELL and 0 <= y < CELL:
            self.px[y][x] = v

    def get(self, x, y):
        return self.px[y][x] if 0 <= x < CELL and 0 <= y < CELL else 0

    def rect(self, x0, y0, x1, y1, v):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, v)

    def hline(self, x0, x1, y, v):
        self.rect(x0, y, x1, y, v)

    def vline(self, x, y0, y1, v):
        self.rect(x, y0, x, y1, v)

    def disk(self, cx, cy, r, v):
        for y in range(CELL):
            for x in range(CELL):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, v)

    def outline(self, v, keep=()):
        """Draws v around every opaque pixel (4-neighbourhood) where the pixel is transparent."""
        add = []
        for y in range(CELL):
            for x in range(CELL):
                if self.px[y][x] == 0 and any(self.get(x + dx, y + dy) not in (0,) + tuple(keep)
                                              for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    add.append((x, y))
        for x, y in add:
            self.set(x, y, v)

    def shift_up(self, n=1):
        self.px = self.px[n:] + [[0] * CELL for _ in range(n)]
        return self

    def copy(self):
        f = Frame()
        f.px = [row[:] for row in self.px]
        return f


def sheet_rows(a, b):
    return [row[:] for row in a.px] + [row[:] for row in b.px]


# ------------------------------------------------------------------------------------------------ the generator
GEN_PAL = [
    MAGENTA,           # 0 transparent
    (16, 12, 22),      # 1 outline
    (44, 50, 62),      # 2 gunmetal dark
    (70, 78, 94),      # 3 gunmetal mid
    (108, 116, 132),   # 4 gunmetal light
    (164, 172, 186),   # 5 steel highlight
    (48, 22, 84),      # 6 violet deep
    (92, 46, 152),     # 7 violet dark
    (142, 86, 216),    # 8 violet mid
    (196, 156, 250),   # 9 violet light
    (248, 238, 255),   # 10 violet white (the core)
    (214, 150, 32),    # 11 amber
    (255, 224, 120),   # 12 amber bright
    (26, 24, 30),      # 13 cable black
    (40, 38, 46),      # 14 skid rubber
    (30, 32, 40),      # 15 dead glass
]


def generator(on, pulse):
    f = Frame()
    # skids (rows 27-29) and the cabinet body (x 8-23, rows 9-26): an 16 px wide box, 3/4 view
    f.rect(6, 27, 25, 28, 14)
    f.hline(7, 24, 29, 13)
    f.hline(6, 25, 27, 13)
    # body front
    f.rect(8, 9, 23, 26, 3)
    f.vline(8, 9, 26, 4)              # lit left edge
    f.vline(23, 9, 26, 2)             # shaded right edge
    f.hline(8, 23, 26, 2)             # bottom lip
    # top face (the vented lid seen from above), rows 4-8, lighter
    f.rect(9, 4, 22, 8, 4)
    f.hline(9, 22, 4, 5)
    f.hline(8, 23, 8, 5)              # front lip catches the light
    for x in (10, 12, 19, 21):        # vent slots either side of the stencil
        f.vline(x, 5, 7, 2)
    # black-sun ring stencil on the lid: a dark disc in a violet ring, eight short rays
    f.hline(14, 17, 5, 7)
    f.hline(14, 17, 7, 7)
    f.set(13, 6, 7), f.set(18, 6, 7)
    f.hline(14, 17, 6, 1)                 # the black sun inside the ring
    f.set(15, 4, 8), f.set(16, 4, 8)      # rays
    f.set(12, 6, 8), f.set(19, 6, 8)
    # window bezel and the shard window (round, centre (15.5, 16.5))
    f.disk(15.5, 16.5, 6.2, 4)
    f.disk(15.5, 16.5, 5.4, 1)
    if on:
        f.disk(15.5, 16.5, 4.6, 6)
        f.disk(15.5, 16.5, 3.8, 7)
        f.disk(15.5, 16.5, 3.0 if pulse else 2.6, 8)
        f.disk(15.5, 16.5, 2.1 if pulse else 1.6, 9)
        f.disk(15.5, 16.5, 1.2 if pulse else 0.8, 10)
        # a shard silhouette across the core, and the glass glint
        f.set(14, 14, 9), f.set(15, 15, 9), f.set(17, 18, 9 if pulse else 8)
        f.set(13, 14, 10 if pulse else 9)
    else:
        f.disk(15.5, 16.5, 4.6, 15)
        f.disk(15.5, 16.5, 3.0, 2)
        f.set(14, 15, 15), f.set(15, 15, 15), f.set(17, 18, 15)
        f.set(13, 14, 4)                  # the glint stays: it's glass
    # bezel highlight upper left, shadow lower right
    for (x, y) in ((11, 12), (12, 11), (13, 11), (11, 13)):
        f.set(x, y, 5)
    for (x, y) in ((20, 21), (19, 22), (18, 22), (20, 20)):
        f.set(x, y, 2)
    # amber status lamp, upper right of the front
    if on:
        f.rect(20, 10, 21, 11, 11)
        f.set(20, 10, 12 if pulse else 11)
    else:
        f.rect(20, 10, 21, 11, 2)
        f.set(20, 10, 3)
    # grille at the bottom of the front
    for y in (23, 25):
        f.hline(10, 21, y, 2)
    f.hline(10, 21, 24, 1)
    # rivets
    for (x, y) in ((9, 10), (22, 10), (9, 25), (22, 25)):
        f.set(x, y, 5)
    # outline the cabinet
    f.outline(1)
    # thick black cable out of the left of the base, running off to the west
    for x, y in ((5, 26), (4, 26), (3, 27), (2, 27), (1, 28), (0, 28)):
        f.set(x, y, 13)
        f.set(x, y + 1, 1)
    f.set(6, 26, 13)
    # the violet power cable out of the right of the base, curling down and away to the east
    cab = 8 if on else 4
    cab_d = 7 if on else 3
    for x, y in ((24, 24), (25, 24), (26, 25), (27, 26), (27, 27), (28, 28), (29, 28), (30, 29), (31, 29)):
        f.set(x, y, cab)
        if f.get(x, y + 1) == 0:
            f.set(x, y + 1, cab_d)
    if on and pulse:                  # current running along the cable
        f.set(27, 26, 9)
    return f.shift_up()               # drawn one row low: the outline under the skids lands on row 29


# -------------------------------------------------------------------------------------------------- the barrier
BAR_PAL = [
    MAGENTA,
    (40, 18, 66),      # 1 deep violet (rare: band core)
    (72, 34, 112),     # 2 dark violet
    (110, 60, 172),    # 3 violet
    (150, 100, 214),   # 4 mid
    (196, 160, 242),   # 5 light
    (236, 222, 255),   # 6 near white
    (255, 255, 255),   # 7 white sparks
] + [(0, 0, 0)] * 8

TOP, BOT = 12, 30


def barrier(phase):
    f = Frame()
    for y in range(TOP, BOT + 1):
        for x in range(CELL):
            t = (y - TOP) / (BOT - TOP)            # 0 at the top edge, 1 at the floor
            # a diagonal band that drifts 4 px per frame; period 16 so neighbours line up
            band = ((x + (y - TOP) // 2 + phase * 4) % 16)
            in_band = band < 5
            # dither: densest near the floor and the edges, open holes in the middle of the curtain
            dense = t > 0.8 or in_band
            hole = ((x + y) % 2 == 0) if not dense else ((x + 2 * y) % 4 == 0)
            if t < 0.35 and not in_band:
                hole = (x + y) % 2 == 0 or (x % 4 == (y // 2) % 4)
            if hole:
                continue
            if in_band:
                v = 5 if band in (1, 2, 3) else 4
            else:
                v = 3 if t > 0.5 else 4 if (x + y) % 3 else 3
            if t > 0.88:
                v = 2 if (x + y) % 2 else 3          # the glow pooling on the floor
            f.set(x, y, v)
    # bright edge lines: the top of the light and the seam on the floor
    for x in range(CELL):
        f.set(x, TOP, 6 if (x + phase * 4) % 16 not in (7, 8) else 5)
        f.set(x, TOP + 1, 5 if x % 2 == phase % 2 else f.get(x, TOP + 1))
        f.set(x, BOT, 4)
        f.set(x, BOT - 1, 5 if (x + phase * 4) % 8 < 4 else 3)
    # sparks that move with the band
    for x0, y0 in ((2, 16), (10, 22), (6, 26), (13, 19)):
        x = (x0 + phase * 4) % 16
        for k in (0, 16):
            f.set(x + k, y0, 7)
    return f


# ------------------------------------------------------------------------------------------------- the dig rope
ROPE_PAL = [
    MAGENTA,
    (40, 28, 18),      # 1 outline
    (86, 56, 30),      # 2 wood dark
    (140, 98, 58),     # 3 wood mid
    (196, 152, 98),    # 4 wood light
    (176, 146, 96),    # 5 rope
    (120, 96, 60),     # 6 rope shadow
    (200, 44, 44),     # 7 flag red
    (120, 24, 30),     # 8 flag red shadow
    (240, 238, 228),   # 9 flag white
    (170, 166, 156),   # 10 flag white shadow
    (204, 160, 44),    # 11 brass
    (255, 226, 120),   # 12 brass highlight
    (110, 80, 20),     # 13 brass shadow
    (52, 46, 40),      # 14 post foot / ground shadow
    (0, 0, 0),
]


def dig_rope(swing):
    f = Frame()
    # two posts: tops at row 13, feet on row 29, 3 px wide with a cap
    for x0 in (6, 23):
        f.rect(x0, 14, x0 + 2, FEET - 1, 3)
        f.vline(x0, 14, FEET - 1, 4)
        f.vline(x0 + 2, 14, FEET - 1, 2)
        f.rect(x0 - 1, 12, x0 + 3, 13, 3)        # cap
        f.hline(x0 - 1, x0 + 3, 12, 4)
        f.hline(x0 - 1, x0 + 3, FEET, 14)        # foot block
        f.hline(x0, x0 + 2, FEET - 1, 2)
        for y in (18, 23):                        # grain
            f.set(x0 + 1, y, 2)
    # the rope sags between the post tops: a shallow curve from (9,15) to (22,15), lowest at row 18
    rope = {}
    for x in range(9, 23):
        u = (x - 15.5) / 6.5
        y = int(round(18 - 3 * u * u))
        rope[x] = y
        f.set(x, y, 5)
        f.set(x, y + 1, 6)
    # pennants hanging from the rope (red, white, red, white): 3 px wide at the rope, tapering to a point
    for i, x in enumerate((9, 12, 17, 20)):
        y = max(rope[x], rope[x + 2]) + 2
        col, sh = ((7, 8) if i % 2 == 0 else (9, 10))
        f.hline(x, x + 2, y, col)
        f.set(x + 2, y, sh)
        f.hline(x, x + 1, y + 1, col)
        f.set(x + 1, y + 1, sh)
        f.set(x, y + 2, col)
    # the bell at the middle, on a short cord; it swings a pixel left/right
    cx = 15 + (-1 if swing else 1)
    top = rope[15] + 2
    f.set(15, top - 1, 6)
    f.set(15 + (0 if not swing else -1), top, 6)
    f.rect(cx - 1, top + 1, cx + 1, top + 3, 11)
    f.hline(cx - 2, cx + 2, top + 3, 11)
    f.set(cx - 1, top + 1, 12)
    f.set(cx - 2, top + 3, 13)
    f.set(cx + 2, top + 3, 13)
    f.set(cx + 1, top + 2, 13)
    f.set(cx, top + 4, 13)                        # clapper
    f.outline(1, keep=())
    return f.shift_up()               # the outline under the post feet lands on row 29


# --------------------------------------------------------------------------------------------- the palette swaps
def to_stone(rgb, warm=(6, 2, -2)):
    r, g, b = rgb[:3]
    lum = 0.30 * r + 0.59 * g + 0.11 * b
    lum = 40 + lum * 0.78
    return tuple(max(0, min(255, int(lum + w))) for w in warm)


def palette_swap(src_name, violet_indices):
    im = png.read(os.path.join(OBJ_DIR, src_name + ".png"))
    assert (im.width, im.height) == (32, 64) and im.indices is not None, src_name
    pal = [tuple(c[:3]) for c in im.palette]
    for i in violet_indices:
        pal[i] = to_stone(pal[i])
    rows = [row[:] for row in im.indices[:32]]
    return rows + [row[:] for row in rows], pal          # frame B = frame A


# ----------------------------------------------------------------------------------------------------- checks
def check(name, rows, pal, problems, rows_allowed=None):
    if len(rows) != 64 or any(len(r) != 32 for r in rows):
        problems.append(f"{name}: sheet is not 32x64")
    if len(pal) > 16:
        problems.append(f"{name}: {len(pal)} colours")
    used = {v for r in rows for v in r}
    if max(used) >= 16:
        problems.append(f"{name}: index >= 16")
    for f0 in (0, 32):
        lit = [y for y in range(32) if any(rows[f0 + y])]
        if not lit:
            problems.append(f"{name}: empty frame")
            continue
        if lit[-1] > 31:
            problems.append(f"{name}: drawn below the cell")
        if rows_allowed:
            lo, hi = rows_allowed
            if lit[0] < lo or lit[-1] > hi:
                problems.append(f"{name}: rows {lit[0]}-{lit[-1]} outside {lo}-{hi}")
        elif lit[-1] != FEET:
            problems.append(f"{name}: lowest pixel on row {lit[-1]} (want {FEET})")


def build():
    sheets = {}
    sheets["shard_generator"] = (sheet_rows(generator(True, False), generator(True, True)), GEN_PAL, None)
    off = generator(False, False)
    sheets["shard_generator_off"] = (sheet_rows(off, off.copy()), GEN_PAL, None)
    sheets["shard_barrier"] = (sheet_rows(barrier(0), barrier(1)), BAR_PAL, (TOP, BOT))
    rows, pal = palette_swap("shard_frame", (6, 7, 8, 9, 10, 11))
    sheets["shard_frame_dark"] = (rows, pal, "same")
    rows, pal = palette_swap("violet_crystal", (5, 6, 7, 8, 9, 10))
    sheets["violet_crystal_dark"] = (rows, pal, "same")
    sheets["dig_rope"] = (sheet_rows(dig_rope(False), dig_rope(True)), ROPE_PAL, None)
    return sheets


def preview(path, rows, pal, scale=8):
    out = []
    for y in range(64):
        line = []
        for x in range(32):
            v = rows[y][x]
            c = ((200, 200, 200) if (x // 2 + y // 2) % 2 else (176, 176, 176)) if v == 0 else pal[v]
            line += [c] * scale
        out += [line] * scale
    png.write_rgba(path, 32 * scale, 64 * scale, out)


def main():
    write = "--write" in sys.argv
    prev = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    problems = []
    sheets = build()
    for name, (rows, pal, mode) in sheets.items():
        if mode == "same":
            src = name.replace("_dark", "")
            lit_src = png.read(os.path.join(OBJ_DIR, src + ".png"))
            if [r for r in lit_src.indices[:32]] != rows[:32]:
                problems.append(f"{name}: pixels differ from {src}")
            check(name, rows, pal, problems, rows_allowed=(0, 31))
        else:
            check(name, rows, pal, problems, rows_allowed=mode)
    if problems:
        print("\n".join(problems))
        return 1
    if prev:
        os.makedirs(prev, exist_ok=True)
        for name, (rows, pal, _) in sheets.items():
            preview(os.path.join(prev, name + "_x8.png"), rows, pal)
    for name, (rows, pal, _) in sheets.items():
        path = os.path.join(OBJ_DIR, name + ".png")
        if write:
            png.write_indexed(path, 32, 64, rows, list(pal) + [(0, 0, 0)] * (16 - len(pal)), bits=4)
        print(("wrote " if write else "ok    ") + os.path.relpath(path, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
