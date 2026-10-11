"""The three Arc 2 idle2 objects (64x32 sheets: frame A, frame B, looped like the Totem idle).

OBJ_EVENT_GFX_ECLIPSE_CRATE (2.17a depot heist, 2.17c the Route 215 night crate, the Haven manifests)
    A wooden shipping crate seen from the usual 3/4 angle: a pale plank lid, a front of horizontal
    planks between two corner posts, steel corner brackets with rivets, and the Team Eclipse mark
    stencilled on the front in violet paint (a dark disc inside a violet ring, with eight short rays:
    the eclipsed sun). Frame B only moves a glint around the painted ring, so a crate never looks alive.

OBJ_EVENT_GFX_SHARD_FRAME (2.5 "Bolted to the wall beside the rift: a cracked metal frame, scorched
violet. Restraints hang from it, empty"; 2.21 the torn Lapras frames)
    An upright steel frame on a wide foot: two riveted posts, a top bar with a black crack through
    it, violet scorch marks on the metal, two short chains hanging inside with open cuffs, and violet
    Eclipse Shard crystals growing out of both top corners and the base. Frame B flashes the crystal
    highlights to other facets and lights a few glow pixels around them (the shards hum).

OBJ_EVENT_GFX_RIFT_ARC2 (every Arc 2 overworld rift: Ravaged Path, Eterna Forest, Route 214,
Route 213, Lost Tower)
    A tall violet tear, larger and rougher than Arc 1's mine rift: a jagged, slightly leaning split in
    the air with torn pale-violet lips, a deep black-violet inside flecked with distant white specks,
    and hairline cracks running out from its tips into the air around it. Frame B pulses: the lips
    widen by a pixel, the cracks glow along their length and the specks move.
"""

from __future__ import annotations

import math

from common import CELL, blank, get_px, neighbours, paint, parse_grid, set_px

# ---------------------------------------------------------------------------
# Eclipse crate
# ---------------------------------------------------------------------------

CRATE_PALETTE = [
    (255, 0, 255),    # 0  transparent
    (34, 22, 18),     # 1  K outline
    (88, 56, 34),     # 2  d wood dark / seams
    (136, 92, 54),    # 3  m wood mid
    (180, 132, 80),   # 4  l wood light
    (218, 178, 118),  # 5  h wood highlight (lid)
    (60, 62, 74),     # 6  s steel dark
    (136, 140, 156),  # 7  S steel light
    (90, 36, 150),    # 8  v violet dark
    (164, 96, 244),   # 9  V violet paint
    (230, 206, 255),  # 10 g glint
    (22, 12, 32),     # 11 o eclipse disc
    (196, 200, 214),  # 12 w rivet
    (0, 0, 0), (0, 0, 0), (0, 0, 0),
]
CRATE_LEGEND = {"K": 1, "d": 2, "m": 3, "l": 4, "h": 5, "s": 6, "S": 7, "v": 8, "V": 9, "g": 10, "o": 11, "w": 12}

CRATE_LID = """
|KKKKKKKKKKKKKKKKKK|
|KhhhhhhhhhhhhhhhhK|
|KllllllllllllldllK|
|KhhhhhhhhhhhhhhhhK|
|KlldllllllllllldlK|
|KKKKKKKKKKKKKKKKKK|
"""

CRATE_FRONT = """
|KSwsmmmmmmmmmmswSK|
|KssllllllllllllssK|
|KmdmmmmmmmmmmmmdmK|
|KmddddddddddddddmK|
|KmdllllllllllllldK|
|KmdmmmmmmmmmmmmdmK|
|KmddddddddddddddmK|
|KmdllllllllllllldK|
|KmdmmmmmmmmmmmmdmK|
|KmddddddddddddddmK|
|KmdllllllllllllldK|
|KmdmmmmmmmmmmmmdmK|
|KssddddddddddddssK|
|KSwsmmmmmmmmmmswSK|
|KKKKKKKKKKKKKKKKKK|
"""

# The Eclipse mark, stencilled: a dark disc in a violet ring with eight short rays.
ECLIPSE_MARK = """
|....V....|
|.V..v..V.|
|..vVVVv..|
|..VoooV..|
|VvVoooVvV|
|..VoooV..|
|..vVVVv..|
|.V..v..V.|
|....V....|
"""


def _crate_base() -> list[int]:
    lid = parse_grid(CRATE_LID)
    f = paint(blank(), lid, CRATE_LEGEND, 7, 9)
    f = paint(f, parse_grid(CRATE_FRONT), CRATE_LEGEND, 7, 15)
    f = paint(f, parse_grid(ECLIPSE_MARK), CRATE_LEGEND, 11, 17)
    return f


# glint positions on the painted ring (frame A, frame B)
CRATE_GLINTS = ([(13, 20), (13, 19)], [(17, 22), (17, 23)])


def crate_frames() -> list[list[int]]:
    frames = []
    base = _crate_base()
    for glints in CRATE_GLINTS:
        f = list(base)
        for x, y in glints:
            if get_px(f, x, y) in (8, 9):
                set_px(f, x, y, 10)
        frames.append(f)
    return frames


# ---------------------------------------------------------------------------
# Shard frame
# ---------------------------------------------------------------------------

FRAME_PALETTE = [
    (255, 0, 255),    # 0  transparent
    (18, 14, 26),     # 1  K outline / crack
    (52, 56, 70),     # 2  s steel dark
    (98, 104, 122),   # 3  S steel mid
    (158, 164, 182),  # 4  L steel light
    (214, 218, 230),  # 5  w steel highlight
    (70, 40, 96),     # 6  u scorch (violet-black)
    (112, 56, 168),   # 7  x scorch violet
    (78, 28, 140),    # 8  v crystal dark
    (150, 84, 236),   # 9  V crystal
    (206, 160, 255),  # 10 c crystal light
    (250, 238, 255),  # 11 g crystal glint
    (84, 70, 60),     # 12 r rust / chain shade
    (0, 0, 0), (0, 0, 0), (0, 0, 0),
]
FRAME_LEGEND = {"K": 1, "s": 2, "S": 3, "L": 4, "w": 5, "u": 6, "x": 7, "v": 8, "V": 9, "c": 10, "g": 11, "r": 12}

SHARD_FRAME = """
|..K..................K..|
|.KcK......K.........KcK.|
|.KVcK....KcK.......KcVVK|
|KvVgVK..KVcVK..K..KVgVvK|
|KvVVVK..KvVVK.KcK.KvVVvK|
|KvVVVKK.KvVVKKVcVKKvVVVK|
|KKKKKKKKKKKKKKKKKKKKKKKK|
|KwLLLLLLLLKLLLLLLxxLLLLK|
|KSSSSSSSSSKKSSSSuxuSSSSK|
|KsssssssssssKsssuusssssK|
|KKKKKKKKKKKKKKKKKKKKKKKK|
|.KwSK..KSK.....KSK..KwSK|
|.KLsK..KrK.....KrK..KLsK|
|.KLsK..KSK.....KSK..KLsK|
|.KLsK..KrK.....KrK..KLxK|
|.KLuK..KSK.....KSK..KLuK|
|.KLxK.KSKSK...KSKSK.KLsK|
|.KLuK.KS.SK...KS.SK.KLsK|
|.KLsK..K.K.....K.K..KLsK|
|.KLsK...............KLsK|
|.KwsK....K..........KLsK|
|.KLsK...KcK...K.....KLsK|
|.KLsK..KVcVK.KcK....KLsK|
|KwLLLLLKvVVVKKVcVKLLLLLK|
|KSSSSSSKvVgVKKvVVKSSSSSK|
|KsssssssKKKKKKKKKKsssssK|
|KKKKKKKKKKKKKKKKKKKKKKKK|
"""

# facets that swap between the frames: (x, y) -> (frame A index, frame B index), in grid coordinates
FRAME_X, FRAME_Y = 4, 3


def frame_frames() -> list[list[int]]:
    rows = parse_grid(SHARD_FRAME)
    base = paint(blank(), rows, FRAME_LEGEND, FRAME_X, FRAME_Y)
    frames = []
    for phase in (0, 1):
        f = list(base)
        if phase:
            # highlights jump to other facets: glints become light, light becomes glint, some mids light up
            for i, v in enumerate(base):
                x, y = i % CELL, i // CELL
                if v == 11:
                    f[i] = 10
                elif v == 10 and (x + y) % 2 == 0:
                    f[i] = 11
                elif v == 9 and (x * 3 + y) % 4 == 0:
                    f[i] = 10
            # a few glow pixels around the shards
            for i, v in enumerate(base):
                if v:
                    continue
                x, y = i % CELL, i // CELL
                if (x + 2 * y) % 3 == 0 and any(n in (9, 10, 11) for _, _, n in neighbours(base, x, y, diagonal=False)):
                    if not any(n in (1,) for _, _, n in neighbours(base, x, y, diagonal=False)) or y < 8:
                        f[i] = 10 if (x + y) % 2 else 9
        frames.append(f)
    return frames


# ---------------------------------------------------------------------------
# Arc 2 rift
# ---------------------------------------------------------------------------

RIFT_PALETTE = [
    (255, 0, 255),    # 0  transparent
    (8, 4, 16),       # 1  void
    (28, 12, 50),     # 2  void mid
    (54, 24, 92),     # 3  void swirl
    (96, 38, 166),    # 4  violet dark (inner lip)
    (150, 82, 236),   # 5  violet
    (208, 168, 255),  # 6  lip light
    (252, 244, 255),  # 7  white hot / specks
    (200, 96, 220),   # 8  magenta fringe
    (120, 60, 190),   # 9  crack glow
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
]

TEAR_TOP, TEAR_BOTTOM = 3, 26
LEAN = 0.18           # x shift per row (the tear leans)
TEAR_HALF = 5.6
JAGS = [0, 1, -1, 1, 0, -1, 1, 1, -1, 0, 1, -1, 0, 1, -1, -1, 1, 0, 1, -1, 0, 1, -1, 0, 0]
CRACKS = [  # polylines (x, y) running out from the tips and sides into the air
    [(13, 3), (11, 1), (12, 0)],
    [(13, 3), (16, 1)],
    [(19, 26), (21, 28), (24, 29)],
    [(19, 26), (17, 29)],
    [(10, 12), (6, 10), (4, 11)],
    [(22, 16), (26, 15), (28, 17)],
    [(11, 19), (7, 21)],
]


def _line(a, b):
    (x0, y0), (x1, y1) = a, b
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(round(x0 + (x1 - x0) * t / n), round(y0 + (y1 - y0) * t / n)) for t in range(n + 1)]


def rift_frame(phase: int) -> list[int]:
    f = blank()
    inside = set()
    n = TEAR_BOTTOM - TEAR_TOP
    for i in range(n + 1):
        y = TEAR_TOP + i
        t = i / n
        w = TEAR_HALF * math.sin(math.pi * t) ** 0.6 + (0.6 if phase else 0.0)
        cx = 13.0 + LEAN * i + 0.7 * math.sin(i * 0.9)
        left = round(cx - w + 0.6 * JAGS[i % len(JAGS)])
        right = round(cx + w - 0.6 * JAGS[(i + 7) % len(JAGS)])
        for x in range(left, right + 1):
            inside.add((x, y))
    depth = {}
    frontier = [p for p in inside if any((p[0] + dx, p[1] + dy) not in inside
                                         for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for p in frontier:
        depth[p] = 0
    d = 0
    while frontier:
        d += 1
        nxt = []
        for x, y in frontier:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if q in inside and q not in depth:
                    depth[q] = d
                    nxt.append(q)
        frontier = nxt
    for (x, y), dd in depth.items():
        if dd == 0:
            c = 6 if (x * 2 + y + phase) % 3 else 7
        elif dd == 1:
            c = 5 if (x + y + phase) % 3 else 6
        elif dd == 2:
            c = 4
        elif dd == 3:
            c = 3 if (x + y) % 3 else 2
        else:
            c = 1 if (x * 3 + y * 5 + phase) % 6 else 2
        set_px(f, x, y, c)
    # distant specks inside the void
    for k in range(9):
        x = 11 + (k * 5 + phase * 2) % 7
        y = 7 + (k * 7 + phase * 3) % 17
        if depth.get((x, y), 0) >= 3:
            set_px(f, x, y, 7 if (k + phase) % 3 else 5)
    # magenta fringe on the outside of the lips (sparse)
    for (x, y), dd in list(depth.items()):
        if dd:
            continue
        for nx, ny, v in neighbours(f, x, y, diagonal=False):
            if v == 0 and (nx * 3 + ny + phase) % 5 == 0:
                set_px(f, nx, ny, 8)
    # hairline cracks
    for line in CRACKS:
        pts = []
        for a, b in zip(line, line[1:]):
            pts += _line(a, b)
        for j, (x, y) in enumerate(pts):
            if get_px(f, x, y) in (0, 8):
                if phase:
                    set_px(f, x, y, 6 if j % 3 == 0 else 9)
                else:
                    set_px(f, x, y, 9 if j % 2 == 0 else 4)
    return f


def rift_frames() -> list[list[int]]:
    return [rift_frame(0), rift_frame(1)]
