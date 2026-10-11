"""OBJ_EVENT_GFX_VIOLET_CRYSTAL (art-final): a cluster of violet crystals growing out of dark rock.

For the Lost Tower vein room in the Distortion World (the four vein/shard deposits around (12..15,22),
sArc2DwLostTowerShard1..4 in src/overlay009/ov9_02249960.c) and any other violet shard deposit.
New pixels, drawn procedurally: five six-sided prisms of different heights leaning out of a low rock mound,
each with a lit left face (pale violet, white glints along the edge), a deep right face and a pointed tip;
a black outline round the whole cluster. Frame B: the glints climb one facet, the faces brighten a step
and a ring of glow pixels lights around the tips (the vein hums), like the shard frame's frame B.
64x32 sheet, two 32x32 idle2 frames, same rules as the other Arc 2 objects.
"""

from __future__ import annotations

from common import CELL, blank, get_px, neighbours, set_px

CRYSTAL_PALETTE = [
    (255, 0, 255),    # 0  transparent
    (16, 10, 26),     # 1  outline
    (40, 34, 52),     # 2  rock dark
    (66, 58, 82),     # 3  rock mid
    (98, 90, 118),    # 4  rock light
    (62, 22, 112),    # 5  crystal deep (right face, shaded)
    (96, 40, 168),    # 6  crystal dark (right face)
    (150, 84, 236),   # 7  crystal mid
    (198, 150, 255),  # 8  crystal light (left face)
    (246, 234, 255),  # 9  glint
    (174, 120, 250),  # 10 glow
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
]
K, RD, RM, RL, CD, CK, CM, CL, CG, GLOW = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

BASE_Y = 27  # rock line the prisms grow from (cell row)
# (base centre x, height above BASE_Y, half width, lean in px per 8 rows)
PRISMS = [
    (9, 11, 2, -4),
    (22, 13, 2, 4),
    (14, 20, 3, -1),
    (18, 15, 2, 2),
    (11, 8, 2, -5),
    (25, 6, 1, 6),
]
ROCK = [(16, 29.0, 12.0, 3.2), (8, 27.6, 5.5, 3.4), (15, 27.2, 4.5, 3.0), (23, 27.4, 5.5, 3.6), (27, 29.0, 3.0, 2.2)]  # ellipses: cx, cy, rx, ry


def _prism(frame: list[int], cx: int, h: int, w: int, lean: int) -> list[tuple[int, int]]:
    """Paint one prism over `frame`; returns its left-edge pixels (for glints)."""
    edge = []
    top = BASE_Y - h
    for y in range(top, BASE_Y + 1):
        t = (BASE_Y - y) / 8.0
        c = cx + round(lean * t)
        tip = y - top  # rows below the tip
        half = min(w, tip // 1) if tip < w + 1 else w
        if tip == 0:
            half = 0
        for x in range(c - half, c + half + 1):
            if x < c:
                v = CL
            elif x == c:
                v = CM
            else:
                v = CK if x < c + half else CD
            set_px(frame, x, y, v)
        edge.append((c - half, y))
    return edge


def _cluster() -> tuple[list[int], list[tuple[int, int]]]:
    f = blank()
    edges = []
    for p in PRISMS:
        edges += _prism(f, *p)
    # rock mound over the prism roots
    for y in range(BASE_Y - 3, CELL):
        for x in range(CELL):
            for cx, cy, rx, ry in ROCK:
                if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0 and y >= BASE_Y - 2:
                    lit = ((x + 0.5 - cx) / rx) < -0.2 and (y + 0.5 - cy) < 0
                    dark = (y + 0.5 - cy) > ry * 0.35
                    v = RL if lit else (RD if dark else RM)
                    set_px(f, x, y, v)
                    break
    # outline
    out = list(f)
    for y in range(CELL):
        for x in range(CELL):
            if get_px(f, x, y):
                continue
            if any(v for _, _, v in neighbours(f, x, y, diagonal=False)):
                set_px(out, x, y, K)
    # separate overlapping prisms: a dark seam where a lit face meets the previous prism's shaded face
    for y in range(CELL):
        for x in range(1, CELL):
            if get_px(f, x, y) == CL and get_px(f, x - 1, y) in (CK, CD):
                set_px(out, x - 1, y, K)
    return out, [p for p in edges if get_px(out, *p) == CL]


def crystal_frames() -> list[list[int]]:
    base, edges = _cluster()
    a = list(base)
    for i, (x, y) in enumerate(edges):
        if i % 3 == 0:
            set_px(a, x, y, CG)
    b = list(base)
    for i, (x, y) in enumerate(edges):
        if i % 3 == 1:
            set_px(b, x, y - 1 if get_px(base, x, y - 1) == CL else y, CG)
    for i, v in enumerate(base):  # faces brighten a step
        if v == CK:
            b[i] = CM if (i % CELL + i // CELL) % 3 == 0 else CK
    for y in range(CELL):  # glow pixels round the upper crystals
        for x in range(CELL):
            if base[y * CELL + x] or y > BASE_Y - 4:
                continue
            near = [v for _, _, v in neighbours(base, x, y, diagonal=True)]
            if K in near and (x * 5 + y * 3) % 4 == 0:
                set_px(b, x, y, GLOW)
    return [a, b]
