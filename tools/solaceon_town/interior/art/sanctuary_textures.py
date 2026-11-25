#!/usr/bin/env python3
"""The Sanctuary hall's textures, painted as 16-colour pixel art in code (standard library only).

Every texture is an indexed image with its own palette (at most 16 colours, pltt16) at stock pixel density
(16 texels per tile for floors and walls, as Hearthome's Foreign Building and the Solaceon News Press). Index 0 is
transparent where the JSON says "c0": 1 (the emblem, the window, the flame, the lily vase).

paint_all() -> {name: (width, height, rows of palette indices, palette [(r, g, b)], meta)}; deterministic.
"""
import math
import random


class Canvas:
    def __init__(self, w, h, fill=0):
        self.w, self.h = w, h
        self.px = [[fill] * w for _ in range(h)]

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def get(self, x, y):
        return self.px[y % self.h][x % self.w]

    def rect(self, x0, y0, x1, y1, c):
        """Inclusive rectangle."""
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                self.px[y][x] = c

    def hline(self, x0, x1, y, c):
        self.rect(x0, y, x1, y, c)

    def vline(self, x, y0, y1, c):
        self.rect(x, y0, x, y1, c)

    def speckle(self, rng, x0, y0, x1, y1, choices, density):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if rng.random() < density:
                    self.set(x, y, rng.choice(choices))


def _t(name, cv, pal, **meta):
    m = {"format": "pltt16", "repeat": [True, True], "c0": 0}
    m.update(meta)
    assert len(pal) <= 16, name
    return name, (cv.w, cv.h, cv.px, pal, m)


# ------------------------------------------------------------------------------------------------ surfaces
def floor():
    """Pale limestone slab, one per tile, warm grey (sampled near set 010's paving greys, a touch warmer)."""
    pal = [(116, 104, 92), (146, 134, 118), (184, 174, 156), (198, 188, 170), (208, 199, 182), (218, 210, 194),
           (228, 221, 206), (170, 160, 142)]
    rng = random.Random(11)
    cv = Canvas(16, 16, 4)
    cv.speckle(rng, 1, 1, 14, 14, [3, 3, 5, 5, 4, 2, 6], 0.55)
    cv.speckle(rng, 2, 2, 13, 13, [7], 0.04)
    cv.hline(0, 15, 15, 1)
    cv.vline(15, 0, 15, 1)
    cv.set(15, 15, 0)
    cv.hline(0, 14, 0, 6)
    cv.vline(0, 0, 14, 6)
    cv.hline(1, 14, 14, 2)
    cv.vline(14, 1, 14, 2)
    return _t("sa_floor", cv, pal)


def planks():
    """The office floor: warm wooden planks running east-west, 4 texels wide, staggered butt joints."""
    pal = [(58, 36, 24), (84, 54, 34), (102, 66, 42), (118, 78, 50), (134, 90, 58), (150, 104, 68), (72, 46, 30)]
    rng = random.Random(12)
    cv = Canvas(16, 16, 3)
    for p in range(4):
        y0 = p * 4
        base = [3, 4, 3, 2][p]
        cv.rect(0, y0, 15, y0 + 3, base)
        cv.speckle(rng, 0, y0 + 1, 15, y0 + 2, [base - 1, base + 1, base], 0.35)
        for x in range(16):
            if rng.random() < 0.18:
                cv.set(x, y0 + rng.choice((1, 2)), 6)
        cv.hline(0, 15, y0, 5 if p != 0 else 5)
        cv.hline(0, 15, y0 + 3, 1)
        j = [3, 11, 7, 14][p]
        cv.vline(j, y0, y0 + 3, 0)
    return _t("sa_planks", cv, pal)


def rug():
    """Plum runner, a small lozenge lattice in muted gold-violet."""
    pal = [(70, 30, 52), (88, 40, 66), (104, 50, 78), (120, 62, 90), (150, 96, 104), (176, 136, 96)]
    cv = Canvas(16, 16, 2)
    rng = random.Random(13)
    cv.speckle(rng, 0, 0, 15, 15, [1, 3, 2], 0.3)
    for y in range(16):
        for x in range(16):
            d = abs((x % 8) - 3.5) + abs((y % 8) - 3.5)
            if 3.0 <= d < 4.0:
                cv.set(x, y, 0)
    for cx, cy in ((3, 3), (11, 11)):
        cv.set(cx, cy, 5)
        cv.set(cx + 1, cy, 4)
        cv.set(cx, cy + 1, 4)
        cv.set(cx + 1, cy + 1, 5)
    return _t("sa_rug", cv, pal)


def hem():
    """Gold hem of the runner, 8 texels across (row 0 = outer edge), a bead every 4 texels."""
    pal = [(60, 26, 46), (130, 92, 40), (186, 140, 64), (222, 182, 96), (244, 214, 140), (98, 64, 30)]
    cv = Canvas(16, 8, 2)
    cv.hline(0, 15, 0, 0)
    cv.hline(0, 15, 1, 1)
    cv.hline(0, 15, 2, 3)
    cv.hline(0, 15, 5, 3)
    cv.hline(0, 15, 6, 1)
    cv.hline(0, 15, 7, 0)
    for x in range(0, 16, 4):
        cv.set(x + 1, 3, 4)
        cv.set(x + 2, 3, 4)
        cv.set(x + 1, 4, 3)
        cv.set(x + 2, 4, 3)
        cv.set(x + 3, 3, 5)
        cv.set(x + 3, 4, 5)
    return _t("sa_hem", cv, pal)


def plaster():
    """Warm cream plaster, softly mottled (16 x 32 = 1 x 2 tiles)."""
    pal = [(200, 186, 162), (212, 199, 175), (222, 210, 187), (230, 220, 199), (238, 230, 211)]
    rng = random.Random(14)
    cv = Canvas(16, 32, 2)
    for _ in range(26):
        x, y, r = rng.randrange(16), rng.randrange(32), rng.choice((1, 1, 2))
        c = rng.choice((1, 3, 3, 1, 4, 0))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r and rng.random() < 0.7:
                    cv.set((x + dx) % 16, (y + dy) % 32, c)
    cv.speckle(rng, 0, 0, 15, 31, [1, 3], 0.12)
    return _t("sa_plaster", cv, pal)


def wainscot():
    """Dark wood panelling, one raised panel per tile, rail on top."""
    pal = [(44, 26, 18), (62, 38, 26), (80, 50, 34), (96, 62, 42), (114, 76, 52), (134, 92, 62), (152, 110, 74)]
    rng = random.Random(15)
    cv = Canvas(16, 16, 3)
    cv.hline(0, 15, 0, 6)
    cv.hline(0, 15, 1, 5)
    cv.hline(0, 15, 2, 2)
    cv.hline(0, 15, 15, 0)
    cv.hline(0, 15, 14, 1)
    cv.vline(0, 3, 13, 4)
    cv.vline(15, 3, 13, 1)
    cv.rect(3, 5, 12, 11, 2)
    cv.speckle(rng, 4, 6, 11, 10, [1, 3], 0.25)
    cv.hline(2, 13, 4, 1)
    cv.vline(2, 4, 12, 1)
    cv.hline(3, 13, 12, 5)
    cv.vline(13, 5, 12, 5)
    return _t("sa_wainscot", cv, pal)


def trim():
    """Gilded moulding for the cornice, ledges and frames (8 texels tall, row 0 = top)."""
    pal = [(84, 58, 30), (128, 92, 46), (172, 130, 70), (206, 164, 92), (234, 204, 138), (110, 76, 38)]
    cv = Canvas(16, 8, 3)
    cv.hline(0, 15, 0, 4)
    cv.hline(0, 15, 1, 3)
    cv.hline(0, 15, 2, 2)
    cv.hline(0, 15, 3, 0)
    cv.hline(0, 15, 6, 4)
    cv.hline(0, 15, 7, 0)
    for x in range(16):
        cv.set(x, 4, 3 if x % 4 in (1, 2) else 5)
        cv.set(x, 5, 2 if x % 4 in (1, 2) else 1)
    return _t("sa_trim", cv, pal)


def wood():
    """Furniture wood (pews, lectern, desk), horizontal grain."""
    pal = [(70, 42, 26), (92, 58, 36), (110, 70, 44), (126, 82, 52), (142, 96, 62), (160, 112, 74), (176, 128, 86)]
    rng = random.Random(16)
    cv = Canvas(16, 16, 3)
    for y in range(16):
        base = 3 + (1 if (y // 3) % 3 == 0 else 0) - (1 if y % 5 == 4 else 0)
        for x in range(16):
            v = base + (1 if rng.random() < 0.15 else 0) - (1 if rng.random() < 0.15 else 0)
            cv.set(x, y, max(1, min(6, v)))
    for y in (0, 8):
        cv.hline(0, 15, y, 5)
    for y in (7, 15):
        cv.hline(0, 15, y, 1)
    cv.set(5, 3, 0)
    cv.set(6, 3, 1)
    cv.set(12, 11, 0)
    return _t("sa_wood", cv, pal)


def brass():
    pal = [(96, 66, 26), (140, 102, 42), (186, 146, 66), (222, 186, 104), (246, 224, 160)]
    cv = Canvas(8, 8, 2)
    cv.hline(0, 7, 0, 4)
    cv.hline(0, 7, 1, 3)
    cv.hline(0, 7, 6, 1)
    cv.hline(0, 7, 7, 0)
    cv.set(2, 3, 3)
    cv.set(5, 4, 1)
    return _t("sa_brass", cv, pal)


# ------------------------------------------------------------------------------------------------ the north wall
def cards():
    """The photo-card board: cork, two rows of cards (a photo, a name and a date each), pins, black mourning
    ribbons, a few white flowers tucked along the bottom. One card's photo is only dark: faintly wrong.
    64 x 32 = 4 x 2 tiles; no frame (the frame is geometry, so the east board can show a shifted copy)."""
    pal = [(98, 66, 40), (120, 84, 52), (140, 100, 62), (160, 118, 76), (236, 228, 208), (200, 190, 168),
           (52, 48, 62), (204, 164, 132), (112, 122, 144), (92, 82, 82), (184, 52, 52), (132, 72, 192),
           (26, 22, 30), (248, 248, 238), (86, 128, 70), (150, 140, 168)]
    rng = random.Random(17)
    cv = Canvas(64, 32, 2)
    cv.speckle(rng, 0, 0, 63, 31, [1, 3, 2, 0], 0.45)
    n = 0
    for row in range(2):
        for col in range(8):
            x0 = 1 + col * 8 + rng.choice((0, 0, 1))
            y0 = 2 + row * 15 + rng.choice((0, 1, 0, -1))
            w, h = 6, 10
            cv.rect(x0, y0, x0 + w - 1, y0 + h - 1, 4)
            cv.vline(x0 + w - 1, y0 + 1, y0 + h - 1, 5)
            cv.hline(x0 + 1, x0 + w - 1, y0 + h - 1, 5)
            # photo 4 x 5
            px0, py0 = x0 + 1, y0 + 1
            dark = (row, col) == (1, 5)
            cv.rect(px0, py0, px0 + 3, py0 + 4, 6 if dark else rng.choice((8, 15, 8)))
            if not dark:
                cv.rect(px0 + 1, py0 + 1, px0 + 2, py0 + 3, 7)       # face
                cv.hline(px0 + 1, px0 + 2, py0 + 1, rng.choice((6, 9, 12, 3)))   # hair
                cv.hline(px0, px0 + 3, py0 + 4, rng.choice((9, 6, 11)))           # shoulders
            # name and date lines
            cv.hline(x0 + 1, x0 + 1 + rng.choice((2, 3, 3)), y0 + 7, 9)
            cv.hline(x0 + 1, x0 + 2, y0 + 8, 9)
            # pin (most red; the violet ones are Eclipse's)
            cv.set(x0 + 2, y0 - 1 if y0 > 0 else y0, 11 if n % 3 == 1 else 10)
            cv.set(x0 + 3, y0 - 1 if y0 > 0 else y0, 11 if n % 3 == 1 else 10)
            if n % 5 == 2:     # a black ribbon across the top-right corner
                cv.set(x0 + w - 1, y0, 12)
                cv.set(x0 + w - 2, y0, 12)
                cv.set(x0 + w - 1, y0 + 1, 12)
            n += 1
    for fx in (5, 22, 41, 57):     # white flowers at the bottom edge
        cv.vline(fx, 28, 31, 14)
        cv.set(fx - 1, 27, 13)
        cv.set(fx + 1, 27, 13)
        cv.set(fx, 26, 13)
        cv.set(fx, 27, 4)
    return _t("sa_cards", cv, pal)


def emblem():
    """The eclipse: a dark disc inside a bright gold ring (the diamond ring at upper right), and a corona of rays,
    long violet rays alternating with short gold ones. Transparent background (c0)."""
    pal = [(0, 0, 0), (22, 14, 34), (40, 26, 60), (66, 40, 100), (102, 66, 152), (142, 104, 196), (188, 164, 228),
           (126, 86, 34), (196, 148, 60), (234, 194, 104), (252, 234, 176), (255, 255, 236)]
    cv = Canvas(64, 64, 0)
    c = 31.5
    for y in range(64):
        for x in range(64):
            dx, dy = x - c, y - c
            r = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            if r < 15.6:
                cv.set(x, y, 1)
            elif r < 17.0:
                cv.set(x, y, 2)
            elif r < 17.9:
                cv.set(x, y, 10)
            elif r < 19.3:
                cv.set(x, y, 9)
            else:
                # 16 rays: even = long violet, odd = short gold; lobes of cos^k
                best, col = 0.0, None
                for k in range(16):
                    ang = k * math.pi / 8 + math.pi / 16
                    d = math.cos(a - ang)
                    if d <= 0:
                        continue
                    lobe = d ** (60 if k % 2 == 0 else 90)
                    reach = (12.2 if k % 2 == 0 else 7.0) * lobe
                    if reach > best:
                        best, col = reach, k % 2
                base = 1.6   # a thin halo all round
                t = (r - 19.3) / max(best, base)
                if r - 19.3 <= max(best, base):
                    if col == 1 and best > base:
                        cv.set(x, y, 9 if t < 0.35 else 8 if t < 0.7 else 7)
                    elif best > base:
                        cv.set(x, y, 6 if t < 0.2 else 5 if t < 0.5 else 4 if t < 0.8 else 3)
                    else:
                        cv.set(x, y, 8 if t < 0.5 else 4)
    # the diamond ring: a bright bead on the ring, upper right
    bx, by = c + 13.0, c - 12.6
    for y in range(64):
        for x in range(64):
            d = math.hypot(x - bx, y - by)
            if d < 1.6:
                cv.set(x, y, 11)
            elif d < 2.8 and cv.get(x, y) not in (1,):
                cv.set(x, y, 10)
    return _t("sa_emblem", cv, pal, c0=1)


def window():
    """A tall lancet window of violet glass with a gold lozenge, lead cames; transparent outside the arch."""
    pal = [(0, 0, 0), (46, 36, 56), (70, 58, 82), (72, 48, 120), (98, 70, 156), (128, 100, 190), (170, 146, 222),
           (210, 196, 240), (200, 156, 72), (240, 206, 120)]
    cv = Canvas(16, 32, 0)
    for y in range(32):
        for x in range(16):
            cx = x - 7.5
            if y >= 8:
                inside = abs(cx) <= 7.5
            else:   # pointed arch: two arcs
                yy = 8 - y
                inside = (abs(cx) + 7.5) ** 2 + yy ** 2 <= 15.0 ** 2 and yy <= 13
            if not inside:
                continue
            edge = abs(cx) > 6.5 or y == 31 or (y < 8 and (abs(cx) + 8.5) ** 2 + (8 - y) ** 2 > 15.0 ** 2)
            if edge:
                cv.set(x, y, 1)
                continue
            band = (y // 4 + int(cx + 8) // 4) % 3
            cv.set(x, y, [3, 4, 5][band])
    for y in range(3, 31):
        cv.set(7, y, 2)
        cv.set(8, y, 2)
    for y in (12, 20, 27):
        cv.hline(1, 14, y, 2)
    for y in range(13, 20):   # the lozenge
        w = 3 - abs(y - 16)
        for x in range(8 - w - 1, 8 + w + 1):
            cv.set(x, y, 9 if abs(y - 16) < 2 and 6 <= x <= 9 else 8)
    for (x, y) in ((4, 9), (11, 23), (3, 24), (12, 14), (5, 29)):
        cv.set(x, y, 7)
        cv.set(x + 1, y, 6)
    return _t("sa_window", cv, pal, c0=1, repeat=[False, False])


def door():
    """The locked back door: dark wood in a stone frame, iron bands, a heavy brass lock, a small violet eclipse."""
    pal = [(26, 18, 16), (52, 32, 24), (70, 44, 32), (88, 58, 42), (106, 72, 52), (40, 40, 50), (74, 74, 88),
           (196, 156, 68), (140, 100, 38), (150, 140, 128), (122, 112, 102), (178, 170, 156), (110, 70, 164),
           (60, 52, 50)]
    rng = random.Random(18)
    cv = Canvas(16, 32, 3)
    for y in range(32):
        for x in range(1, 15):
            cv.set(x, y, [2, 3, 3, 4][(x // 3 + (1 if rng.random() < 0.1 else 0)) % 4])
    for x in (4, 7, 10, 13):
        cv.vline(x, 3, 31, 1)
    for y in range(4):   # rounded head
        for x in range(16):
            if (x - 7.5) ** 2 + ((4 - y) * 1.8) ** 2 > 7.5 ** 2:
                cv.set(x, y, 13)
    for y in range(32):
        cv.set(0, y, 11 if y % 6 else 10)
        cv.set(15, y, 10 if y % 6 else 9)
    for y in range(4):
        for x in range(1, 15):
            if cv.get(x, y) != 13 and (x - 7.5) ** 2 + ((4 - y) * 1.8) ** 2 > 6.2 ** 2:
                cv.set(x, y, 11)
    for y in (10, 23):
        cv.hline(1, 14, y, 5)
        cv.hline(1, 14, y + 1, 6)
        for x in (3, 8, 12):
            cv.set(x, y, 6)
    cv.rect(10, 14, 13, 19, 8)
    cv.rect(10, 14, 13, 14, 7)
    cv.vline(10, 14, 19, 7)
    cv.set(11, 16, 0)
    cv.set(11, 17, 0)
    cv.set(12, 17, 0)
    for (x, y) in ((6, 5), (7, 4), (8, 4), (9, 5), (9, 6), (8, 7), (7, 7), (6, 6)):
        cv.set(x, y, 12)
    cv.hline(1, 14, 31, 0)
    return _t("sa_door", cv, pal, repeat=[False, False])


def sconce_flame():
    """A candle flame (8 x 16, transparent around it): white core, yellow, orange rim, a blue foot."""
    pal = [(0, 0, 0), (232, 120, 40), (250, 176, 70), (252, 222, 120), (255, 248, 220), (110, 120, 210),
           (60, 40, 30)]
    cv = Canvas(8, 16, 0)
    for y in range(16):
        for x in range(8):
            t = (y - 2) / 11.0
            if t < 0 or t > 1:
                continue
            half = 3.2 * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.8 if t < 0.87 else 1.0
            d = abs(x - 3.5)
            if d > half:
                continue
            k = d / max(half, 0.01)
            cv.set(x, y, 4 if k < 0.35 and 0.35 < t < 0.85 else 3 if k < 0.6 else 2 if k < 0.85 else 1)
    cv.set(3, 13, 5)
    cv.set(4, 13, 5)
    cv.set(3, 14, 6)
    cv.set(4, 14, 6)
    cv.set(3, 15, 6)
    return _t("sa_flame", cv, pal, c0=1, repeat=[False, False])


def lily_vase():
    """White lilies in a pale porcelain vase (16 x 32, transparent around it), a billboard for the entrance."""
    pal = [(0, 0, 0), (40, 70, 40), (64, 104, 56), (96, 140, 74), (250, 250, 242), (226, 224, 214),
           (196, 192, 184), (236, 200, 96), (170, 180, 196), (206, 214, 226), (232, 238, 244), (120, 128, 150)]
    rng = random.Random(19)
    cv = Canvas(16, 32, 0)
    # vase: rows 18..31
    for y in range(18, 32):
        t = (y - 18) / 13.0
        half = 2.4 + 3.2 * math.sin(math.pi * min(1.0, t * 0.95 + 0.05)) if y > 19 else 3.0
        for x in range(16):
            d = x - 7.5
            if abs(d) <= half:
                cv.set(x, y, 10 if d < -half * 0.3 else 9 if d < half * 0.4 else 8)
    cv.hline(5, 10, 18, 11)
    cv.hline(5, 10, 31, 11)
    # stems and leaves
    for sx, top in ((7, 6), (5, 9), (10, 8), (8, 4), (3, 12), (12, 11)):
        for y in range(top + 2, 19):
            cv.set(sx + (1 if (y + sx) % 7 == 0 else 0), y, 2)
    for _ in range(14):
        x, y = rng.randrange(2, 14), rng.randrange(10, 18)
        cv.set(x, y, rng.choice((1, 3, 2)))
    # lily heads: 6-pixel stars
    for sx, top in ((7, 6), (5, 9), (10, 8), (8, 4), (3, 12), (12, 11)):
        for dx, dy, c in ((0, 0, 7), (-1, 0, 4), (1, 0, 4), (0, -1, 4), (0, 1, 5), (-2, -1, 5), (2, -1, 5),
                          (-1, 1, 6), (1, 1, 6), (0, -2, 4)):
            cv.set(sx + dx, top + dy, c)
    return _t("sa_lily", cv, pal, c0=1, repeat=[False, False])


# ------------------------------------------------------------------------------------------------ the office
def files():
    """Records shelf front (1 x 2 tiles): binders on the upper shelf, card drawers below, dark shelf boards."""
    pal = [(40, 26, 18), (66, 42, 28), (96, 62, 40), (150, 110, 74), (180, 140, 98), (110, 40, 44), (52, 60, 98),
           (82, 100, 60), (214, 204, 176), (122, 82, 56), (196, 156, 68), (90, 72, 110), (160, 150, 130)]
    rng = random.Random(20)
    cv = Canvas(16, 32, 2)
    for y in (0, 15, 30):
        cv.hline(0, 15, y, 2)
        cv.hline(0, 15, y + 1, 0)
    cv.vline(0, 0, 31, 1)
    cv.vline(15, 0, 31, 0)
    x = 1
    while x < 15:   # binders
        w = rng.choice((2, 2, 3))
        col = rng.choice((5, 6, 7, 11, 12, 9, 6))
        top = rng.choice((2, 3, 3, 4))
        cv.rect(x, top, min(14, x + w - 1), 14, col)
        cv.rect(x, top + 3, min(14, x + w - 1), top + 4, 8)
        x += w
    cv.rect(1, 17, 14, 29, 3)   # drawers
    for (x0, y0) in ((1, 17), (8, 17), (1, 23), (8, 23)):
        cv.rect(x0, y0, x0 + 6, y0 + 5, 4)
        cv.hline(x0, x0 + 6, y0 + 5, 9)
        cv.vline(x0 + 6, y0, y0 + 5, 9)
        cv.rect(x0 + 2, y0 + 1, x0 + 4, y0 + 2, 8)
        cv.set(x0 + 3, y0 + 3, 10)
    return _t("sa_files", cv, pal)


def box():
    """A cardboard card box with a white label."""
    pal = [(98, 70, 40), (140, 104, 64), (170, 132, 86), (190, 152, 104), (208, 172, 122), (236, 232, 220),
           (120, 110, 100), (160, 150, 120)]
    rng = random.Random(21)
    cv = Canvas(16, 16, 3)
    cv.speckle(rng, 0, 0, 15, 15, [2, 4], 0.2)
    cv.hline(0, 15, 0, 4)
    cv.vline(0, 0, 15, 4)
    cv.hline(0, 15, 15, 0)
    cv.vline(15, 0, 15, 1)
    cv.hline(1, 14, 7, 7)
    cv.rect(4, 3, 11, 6, 5)
    cv.hline(5, 9, 4, 6)
    cv.hline(5, 7, 5, 6)
    return _t("sa_box", cv, pal)


def ledger():
    """An open ledger seen from above: leather boards, cream pages with ruled columns of names, a red ribbon."""
    pal = [(54, 24, 22), (84, 36, 30), (240, 232, 210), (222, 212, 186), (176, 166, 146), (110, 100, 96),
           (180, 40, 40), (200, 190, 168)]
    cv = Canvas(16, 16, 1)
    cv.rect(0, 0, 15, 15, 0)
    cv.rect(1, 2, 14, 13, 2)
    cv.vline(7, 2, 13, 4)
    cv.vline(8, 2, 13, 7)
    for y in range(3, 13, 2):
        cv.hline(2, 6, y, 5 if y % 4 == 3 else 4)
        cv.hline(9, 13, y, 5 if y % 4 == 1 else 4)
    cv.rect(1, 13, 14, 13, 3)
    cv.vline(10, 13, 15, 6)
    return _t("sa_ledger", cv, pal)


def sinnoh_map():
    """A map of Sinnoh pinned with violet pins (32 x 16 = 2 x 1 tiles), in a thin wooden frame."""
    pal = [(66, 42, 28), (150, 168, 176), (132, 150, 160), (214, 196, 150), (190, 170, 124), (150, 130, 96),
           (132, 72, 192), (184, 52, 52), (236, 226, 196)]
    cv = Canvas(32, 16, 1)
    for y in range(16):
        for x in range(32):
            if (x + y) % 5 == 0:
                cv.set(x, y, 2)
    # a rough Sinnoh: the main island, the north-east hook, the Coronet ridge
    land = [(4, 3, 24, 12), (8, 2, 20, 3), (21, 4, 27, 7), (24, 2, 28, 4), (6, 12, 14, 13), (16, 12, 22, 13)]
    for x0, y0, x1, y1 in land:
        cv.rect(x0, y0, x1, y1, 3)
    for x0, y0, x1, y1 in ((4, 3, 6, 5), (22, 10, 24, 12), (12, 11, 14, 12)):
        cv.rect(x0, y0, x1, y1, 1)
    for y in range(3, 12):
        cv.set(14 + (y % 3 == 0), y, 5)
        cv.set(15, y, 4)
    for (x, y, c) in ((9, 6, 6), (19, 9, 6), (12, 10, 6), (25, 5, 6), (17, 4, 7), (7, 9, 6), (21, 7, 6)):
        cv.set(x, y, c)
    cv.rect(0, 0, 31, 0, 0)
    cv.rect(0, 15, 31, 15, 0)
    cv.vline(0, 0, 15, 0)
    cv.vline(31, 0, 15, 0)
    return _t("sa_map", cv, pal, repeat=[False, False])


def paint_all():
    return dict(f() for f in (floor, planks, rug, hem, plaster, wainscot, trim, wood, brass, cards, emblem, window,
                              door, sconce_flame, lily_vase, files, box, ledger, sinnoh_map))
