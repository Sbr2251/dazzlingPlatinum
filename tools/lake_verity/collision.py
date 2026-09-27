#!/usr/bin/env python3
"""Permissions and BDHC for the Lake Verity chunks, generated from layout.py. Standard library only.

permissions(chunk)  -> 0x800 bytes: layout.tiles() collision values, [z][x]
bdhc(chunk)         -> BDHC bytes:
    * every tile gets its layout height h at world y = 16 + 16 * h (water h -0.5 -> y 8, as stock);
    * flat areas are merged into maximal rectangles (on a half-tile grid, so slopes can start at tile centres);
    * each SLOPES entry becomes one sloped plate per chunk it crosses. The stair slope runs from the landing's tile
      centre (h F1_H) to the courtyard tile centre below the stair (h 0), so it passes exactly through
      layout.stair_height() at each stair tile centre and joins both flat areas without a step.
check(chunk, raw)   -> list of tiles whose BDHC height at the tile centre differs from layout h (empty = good)

Usage: python3 tools/lake_verity/collision.py [check]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout  # noqa: E402
import mapdata  # noqa: E402

FX = 4096
GROUND_Y = 16          # world y of h = 0
TILE = 16


def world_y(h):
    return GROUND_Y + TILE * h


def slopes():
    """[(x0, x1, z_top, z_bottom, h_top, h_bottom)] in continuous tile coordinates (x1 exclusive). Height is linear
    in z between z_top (north) and z_bottom (south)."""
    x0, z0, x1, z1 = layout.STAIR
    # tile centres: landing row above the stair (z0 - 1) at F1_H, courtyard row below (z1 + 1) at 0
    return [(x0, x1 + 1, z0 - 0.5, z1 + 1.5, float(layout.F1_H), 0.0)]


def _merge(cells, n):
    """cells: n x n grid [z][x] of hashable values (None = no plate). Greedy maximal rectangles, row-major.
    -> [(x0, z0, x1, z1, value)] with x1, z1 exclusive."""
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


def _slope_plane(z_top, z_bottom, h_top, h_bottom, cz):
    """Plane for y = f(z_local) through the two heights -> (normal, d) in fx32, chunk-local coordinates."""
    zl = lambda zt: ((zt - cz * 32) * TILE - 256)   # noqa: E731
    za, zb = zl(z_top), zl(z_bottom)
    ya, yb = world_y(h_top), world_y(h_bottom)
    a = (yb - ya) / (zb - za)            # dy/dz
    c = ya - a * za                      # y = a z + c
    inv = 1 / math.sqrt(1 + a * a)
    ny, nz = round(FX * inv), round(-a * FX * inv)
    # y = -(nz z + d) / ny  ->  d = -(ny y + nz z) at z = 0
    d = round(-(ny * c * FX) / FX)
    return (0, ny, nz), d


def plates(chunk):
    cx, cz = layout.CHUNKS[chunk]
    t = layout.tiles()
    n = 64                                # half tiles per chunk side
    cells = [[None] * n for _ in range(n)]
    for hz in range(n):
        for hx in range(n):
            x, z = cx * 32 + hx // 2, cz * 32 + hz // 2
            cells[hz][hx] = t[(x, z)][1]
    sl = []
    for x0, x1, zt, zb, ht, hb in slopes():
        hx0, hx1 = (x0 - cx * 32) * 2, (x1 - cx * 32) * 2
        hz0, hz1 = round((zt - cz * 32) * 2), round((zb - cz * 32) * 2)
        cx0, cx1, cz0, cz1 = max(hx0, 0), min(hx1, n), max(hz0, 0), min(hz1, n)
        if cx0 >= cx1 or cz0 >= cz1:
            continue
        for hz in range(cz0, cz1):
            for hx in range(cx0, cx1):
                cells[hz][hx] = None
        sl.append((cx0, cz0, cx1, cz1, (zt, zb, ht, hb)))
    out = []
    to_l = lambda half: (half * TILE // 2 - 256) * FX   # noqa: E731
    for x0, z0, x1, z1, h in _merge(cells, n):
        out.append((to_l(x0), to_l(z0), to_l(x1), to_l(z1), (0, FX, 0), int(round(-world_y(h) * FX))))
    for x0, z0, x1, z1, (zt, zb, ht, hb) in sl:
        nrm, d = _slope_plane(zt, zb, ht, hb, cz)
        out.append((to_l(x0), to_l(z0), to_l(x1), to_l(z1), nrm, d))
    return out


def permissions(chunk):
    cx, cz = layout.CHUNKS[chunk]
    t = layout.tiles()
    return mapdata.write_permissions([[t[(cx * 32 + x, cz * 32 + z)][0] for x in range(32)] for z in range(32)])


def bdhc(chunk):
    return mapdata.write_bdhc(mapdata.build_bdhc(plates(chunk)))


def check(chunk, raw, tol=0):
    """-> [(x, z, layout h, bdhc h)] for tile centres where the BDHC height (world units, fx32) differs from the
    layout by more than tol fx32 units."""
    cx, cz = layout.CHUNKS[chunk]
    t = layout.tiles()
    b = mapdata.read_bdhc(raw)
    bad = []
    for lz in range(32):
        for lx in range(32):
            want = world_y(t[(cx * 32 + lx, cz * 32 + lz)][1]) * FX
            x, z = mapdata.tile_centre(lx, lz)
            got = mapdata.height_at(b, x, z, current=want)
            if got is None or abs(got - round(want)) > tol:
                bad.append((cx * 32 + lx, cz * 32 + lz, t[(cx * 32 + lx, cz * 32 + lz)][1],
                            None if got is None else (got / FX - GROUND_Y) / TILE))
    return bad


def main():
    for c in (537, 538, 540, 541):
        raw = bdhc(c)
        exact = check(c, raw)
        near = check(c, raw, tol=16)       # 16 fx32 = 1/256 world unit
        b = mapdata.read_bdhc(raw)
        print(f"chunk {c}: {len(b['plates'])} plates, {len(b['strips'])} strips, {len(raw)} bytes; "
              f"tile centres off: {len(exact)} exact, {len(near)} beyond 1/256 unit {exact[:4]}")


if __name__ == "__main__":
    main()
