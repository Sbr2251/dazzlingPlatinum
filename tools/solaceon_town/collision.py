#!/usr/bin/env python3
"""Permissions and BDHC for Solaceon Town (map_data_072/073), generated from layout.py. Standard library only.
Adapted from tools/lake_verity/collision.py (same plate merge and BDHC writer; the town is flat, so no slopes).

permissions(c)   -> 0x800 bytes: layout.tiles() collision values, [z][x]
bdhc(c)          -> BDHC bytes: every tile at world y = 16 + 16 * h, equal heights merged into maximal rectangles
check(c, raw)    -> tiles whose BDHC height at the tile centre differs from the layout (empty = good)

Usage: python3 tools/solaceon_town/collision.py      (prints plates / sizes / mismatches per chunk)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
sys.path.insert(0, HERE)            # first, so "layout" is tools/solaceon_town/layout.py, not Lake Verity's

import layout  # noqa: E402  (tools/solaceon_town/layout.py)
import mapdata  # noqa: E402

FX = 4096
TILE = 16


def world_y(h):
    return 16 + TILE * h


def _merge(cells, n):
    """cells: n x n [z][x] of hashable values (None = no plate). Greedy maximal rectangles, row-major.
    -> [(x0, z0, x1, z1, value)], x1 / z1 exclusive (as tools/lake_verity/collision.py)."""
    used = [[False] * n for _ in range(n)]
    out = []
    for z in range(n):
        for x in range(n):
            v = cells[z][x]
            if used[z][x] or v is None:
                continue
            w = 1
            while x + w < n and not used[z][x + w] and cells[z][x + w] == v:
                w += 1
            d = 1
            while z + d < n and all(not used[z + d][x + k] and cells[z + d][x + k] == v for k in range(w)):
                d += 1
            for dz in range(d):
                for k in range(w):
                    used[z + dz][x + k] = True
            out.append((x, z, x + w, z + d, v))
    return out


def plates(c):
    cx, cz = layout.CHUNKS[c]
    t = layout.tiles()
    cells = [[t[(cx * 32 + x, cz * 32 + z)][1] for x in range(32)] for z in range(32)]
    to_l = lambda k: (k * TILE - 256) * FX   # noqa: E731
    return [(to_l(x0), to_l(z0), to_l(x1), to_l(z1), (0, FX, 0), int(round(-world_y(h) * FX)))
            for x0, z0, x1, z1, h in _merge(cells, 32)]


def permissions(c):
    cx, cz = layout.CHUNKS[c]
    t = layout.tiles()
    return mapdata.write_permissions([[t[(cx * 32 + x, cz * 32 + z)][0] for x in range(32)] for z in range(32)])


def bdhc(c):
    return mapdata.write_bdhc(mapdata.build_bdhc(plates(c)))


def check(c, raw, tol=0):
    """-> [(x, z, layout h, bdhc h)] for tile centres where the BDHC height differs from the layout."""
    cx, cz = layout.CHUNKS[c]
    t = layout.tiles()
    b = mapdata.read_bdhc(raw)
    bad = []
    for lz in range(32):
        for lx in range(32):
            x, z = cx * 32 + lx, cz * 32 + lz
            want = world_y(t[(x, z)][1]) * FX
            got = mapdata.height_at(b, *mapdata.tile_centre(lx, lz), current=round(want))
            if got is None or abs(got - round(want)) > tol:
                bad.append((x, z, t[(x, z)][1], None if got is None else (got / FX - 16) / TILE))
    return bad


def check_permissions(c, raw):
    """-> [(x, z, layout value, map value)] where the permissions differ from the layout."""
    cx, cz = layout.CHUNKS[c]
    t = layout.tiles()
    p = mapdata.read_permissions(raw)
    return [(cx * 32 + x, cz * 32 + z, t[(cx * 32 + x, cz * 32 + z)][0], p[z][x])
            for z in range(32) for x in range(32) if p[z][x] != t[(cx * 32 + x, cz * 32 + z)][0]]


def main():
    for c in layout.CHUNKS:
        raw = bdhc(c)
        b = mapdata.read_bdhc(raw)
        print(f"chunk {c}: {len(b['plates'])} plates, {len(b['strips'])} strips, {len(raw)} B BDHC; "
              f"tile centres off the layout: {len(check(c, raw))}; permissions off: "
              f"{len(check_permissions(c, permissions(c)))}")


if __name__ == "__main__":
    main()
