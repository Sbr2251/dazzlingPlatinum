"""The two idle2 objects: the Arc 1 rift and the violet totem Hitmonlee.

idle2 sheets are 64x32: frame A then frame B, looped by the engine like the Totem idle
and shown the same for every facing.

OBJ_EVENT_GFX_ARC1_RIFT
    "Deep in the mine: where the sealed wall was, a small violet rift hangs in the air."
    A jagged vertical tear floating above the ground: a black-violet void with swirls,
    a hot violet rim, a pale glow and a few drifting shards. Frame B breathes: the
    tear narrows by a pixel, the rim glow flickers to the other pixels and the shards
    drift up. Generated procedurally (deterministic, no randomness).

OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET
    "Through the rift, a huge silhouette rears up and roars: a Hitmonlee, far too big,
    wreathed in a violet aura." The stock totem Hitmonlee frames
    (res/field/objects/totems/hitmonlee_idle_{a,b}.png) recoloured to a dark violet
    silhouette with glowing eyes, wrapped in a two-pixel violet aura whose outer ring
    and rising wisps alternate between the frames so the aura shimmers.
"""

from __future__ import annotations

import math

from pixelkit import CELL, REPO_ROOT, blank, neighbours, read_png

# ---------------------------------------------------------------------------
# Rift
# ---------------------------------------------------------------------------

RIFT_PALETTE = [
    (255, 0, 255),    # 0  transparent
    (10, 6, 18),      # 1  void (deepest)
    (34, 14, 58),     # 2  void
    (62, 28, 104),    # 3  void swirl
    (104, 40, 176),   # 4  violet dark
    (164, 92, 244),   # 5  violet
    (224, 196, 255),  # 6  glow
    (255, 255, 255),  # 7  white hot
    (236, 120, 236),  # 8  magenta fringe
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
]

RIFT_TOP, RIFT_BOTTOM = 5, 25        # tear rows (the crack tips reach 1 px further)
RIFT_CX = 15.5
RIFT_HALF_WIDTH = 4.8
JAG = [0, 1, 1, 0, -1, 0, 1, 0, -1, -1, 0, 1, 0, 0, -1, 0, 1, 1, 0, -1, 0]  # edge zigzag per row
MEANDER = [0, 0, 1, 1, 1, 0, 0, -1, -1, 0, 0, 1, 1, 0, 0, -1, -1, -1, 0, 0, 0]  # crack drift per row


def _rift_rows(phase: int):
    """Yield (y, left, right) inclusive spans of the tear for one frame."""
    n = RIFT_BOTTOM - RIFT_TOP
    for i in range(n + 1):
        y = RIFT_TOP + i
        t = i / n
        width = RIFT_HALF_WIDTH * math.sin(math.pi * t) ** 0.75 - (0.35 if phase else 0.0)
        if width < 0.5:
            width = 0.5
        centre = RIFT_CX + 0.6 * MEANDER[i]
        left = round(centre - width + 0.5 * JAG[i])
        right = round(centre + width - 0.5 * JAG[(i + 5) % len(JAG)]) - 1
        if right < left:
            right = left
        yield y, left, right


def rift_frame(phase: int) -> list[int]:
    f = blank()
    spans = list(_rift_rows(phase))
    inside = set()
    for y, l, r in spans:
        for x in range(l, r + 1):
            inside.add((x, y))
    # crack tips above and below
    top_x = spans[0][1]
    bottom_x = spans[-1][1]
    tips = [(top_x, RIFT_TOP - 1), (top_x + 1, RIFT_TOP - 2), (bottom_x, RIFT_BOTTOM + 1), (bottom_x - 1, RIFT_BOTTOM + 2)]
    for x, y in inside:
        f[y * CELL + x] = 1
    # depth of every inside pixel: 0 on the edge, +1 per step inwards
    depth = {}
    frontier = [(x, y) for x, y in inside
                if any((x + dx, y + dy) not in inside for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
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
    # rim hot and flickering, then violet, then a dark core with a slow swirl
    for (x, y), d in depth.items():
        if d == 0:
            c = 6 if (x + y + phase) % 3 == 0 else 5
        elif d == 1:
            c = 5 if (x * 2 + y + phase) % 4 == 0 else 4
        elif d == 2:
            c = 3 if (x + y * 2 + phase) % 5 else 4
        else:
            c = 3 if (x + 2 * y + 3 * phase) % 7 == 0 else (1 if (x - y + phase) % 4 == 0 else 2)
        f[y * CELL + x] = c
    # outer glow: transparent pixels touching the rim
    glow = []
    for y in range(CELL):
        for x in range(CELL):
            if f[y * CELL + x]:
                continue
            if any(v in (5, 6) for _, _, v in neighbours(f, x, y, diagonal=False)):
                glow.append((x, y))
    for x, y in glow:
        k = (x * 3 + y + phase * 2) % 4
        f[y * CELL + x] = {0: 6, 1: 4, 2: 4, 3: 8 if (x + y) % 3 == 0 else 0}[k]
    for x, y in tips:
        f[y * CELL + x] = 6
    # brightest points: one white-hot pixel at the widest part of each edge
    mid = spans[len(spans) // 2 + (1 if phase else -1)]
    y, l, r = mid
    f[y * CELL + l] = 7
    f[(y + 2) * CELL + r] = 7 if phase == 0 else 6
    # drifting shards (2x2 / 1x2 chips) that rise between frames
    shards = [(9, 12), (22, 9), (21, 20), (8, 22)]
    for i, (x, y) in enumerate(shards):
        y -= phase * (1 + i % 2)
        colour = 6 if (i + phase) % 2 else 5
        f[y * CELL + x] = colour
        f[(y + 1) * CELL + x] = 4
        if i % 2 == 0:
            f[y * CELL + x + 1] = 4
    # a faint glow on the ground under the floating tear
    for x in range(13, 19):
        if (x + phase) % 2 == 0:
            f[28 * CELL + x] = 4
    for x in range(14, 18):
        if (x + phase) % 2 == 1:
            f[29 * CELL + x] = 3
    return f


def rift_frames() -> list[list[int]]:
    return [rift_frame(0), rift_frame(1)]


# ---------------------------------------------------------------------------
# Violet totem Hitmonlee
# ---------------------------------------------------------------------------

HITMONLEE_PALETTE = [
    (255, 0, 255),    # 0  transparent
    (16, 8, 28),      # 1  outline
    (40, 20, 66),     # 2  body dark
    (56, 30, 92),     # 3  body mid
    (84, 48, 130),    # 4  body light
    (116, 78, 168),   # 5  body highlight
    (176, 148, 224),  # 6  wraps light
    (112, 88, 164),   # 7  wraps dark
    (255, 214, 255),  # 8  eye glow
    (168, 96, 248),   # 9  aura
    (108, 44, 184),   # 10 aura dark
    (228, 200, 255),  # 11 aura glow
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
]

# Stock totem palette: 1 white, 2 black, 3 light brown, 4 dark brown, 5 grey, 6 tan,
# 7 dark grey, 8 light grey, 9 mid brown, A dark red-brown, B olive, C tan.
HITMONLEE_MAP = {1: 8, 2: 1, 3: 4, 4: 2, 5: 7, 6: 5, 7: 2, 8: 6, 9: 3, 10: 2, 11: 3, 12: 4}

TOTEM_DIR = REPO_ROOT / "res/field/objects/totems"


def _aura(frame: list[int], phase: int) -> list[int]:
    body = list(frame)
    out = list(frame)
    ground = 29  # keep the feet planted: no aura below the lowest body row
    ring1 = set()
    for y in range(CELL):
        for x in range(CELL):
            if body[y * CELL + x] or y > ground:
                continue
            if any(v for _, _, v in neighbours(body, x, y, diagonal=True)):
                ring1.add((x, y))
    for x, y in ring1:
        out[y * CELL + x] = 9
    ring2 = set()
    for y in range(CELL):
        for x in range(CELL):
            if out[y * CELL + x] or y > ground:
                continue
            if any((nx, ny) in ring1 for nx, ny, _ in neighbours(out, x, y, diagonal=False)):
                ring2.add((x, y))
    for x, y in ring2:
        if (x + y + phase) % 2 == 0:
            out[y * CELL + x] = 10
    # glints on the inner ring
    for x, y in ring1:
        if (x * 5 + y * 3 + phase * 4) % 9 == 0:
            out[y * CELL + x] = 11
    # wisps rising off the head and shoulders
    wisps = [(11, 7), (14, 5), (17, 6), (20, 8), (7, 14), (24, 13)]
    for i, (x, y) in enumerate(wisps):
        if (i + phase) % 2:
            continue
        for k, colour in enumerate((11, 9, 10)):
            yy = y + k - phase
            if 0 <= yy < CELL and not body[yy * CELL + x]:
                out[yy * CELL + x] = colour
    return out


def hitmonlee_frames() -> list[list[int]]:
    frames = []
    for phase, name in enumerate(("hitmonlee_idle_a.png", "hitmonlee_idle_b.png")):
        width, height, pixels, _ = read_png(TOTEM_DIR / name)
        if (width, height) != (CELL, CELL):
            raise ValueError(f"{name}: expected 32x32")
        body = [HITMONLEE_MAP.get(v, v) if v else 0 for v in pixels]
        frames.append(_aura(body, phase))
    return frames
