#!/usr/bin/env python3
"""Permissions (32x32 u16) and BDHC heightfields for Route 218 — Everspring Sanctuary
(map_data_050.bin and map_data_051.bin), generated from tools/everspring/layout.py.

Usage:
  python3 tools/everspring/collision.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
sys.path.insert(0, HERE)

import layout  # noqa: E402
import mapdata  # noqa: E402

FX = 4096
TILE = 16


def world_y(h):
    """Layout h -> BDHC world y (h=0.0 -> 16.0, h=-0.5 -> 8.0, matching stock map_data_050/051)."""
    return 16.0 + TILE * h


def _merge(cells, n):
    """Greedy maximal rectangles over an n x n [z][x] grid -> [(x0, z0, x1, z1, value)]."""
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


def plates(cid):
    cx, cz = layout.CHUNKS[cid]
    grid = layout.tiles()
    cells = [[grid[(cx * 32 + lx, cz * 32 + lz)][1] for lx in range(32)] for lz in range(32)]
    to_local = lambda k: (k * TILE - 256) * FX  # noqa: E731
    return [
        (to_local(x0), to_local(z0), to_local(x1), to_local(z1), (0, FX, 0), int(round(-world_y(h) * FX)))
        for x0, z0, x1, z1, h in _merge(cells, 32)
    ]


def permissions(cid):
    cx, cz = layout.CHUNKS[cid]
    grid = layout.tiles()
    return mapdata.write_permissions(
        [[grid[(cx * 32 + lx, cz * 32 + lz)][0] for lx in range(32)] for lz in range(32)]
    )


def bdhc(cid):
    return mapdata.write_bdhc(mapdata.build_bdhc(plates(cid)))


def check_bdhc(cid, raw, tol=0):
    """Return [(x, z, want_h, got_h)] where BDHC height at tile centre differs from layout."""
    cx, cz = layout.CHUNKS[cid]
    grid = layout.tiles()
    b = mapdata.read_bdhc(raw)
    bad = []
    for lz in range(32):
        for lx in range(32):
            wx, wz = cx * 32 + lx, cz * 32 + lz
            want_h = grid[(wx, wz)][1]
            want_fx = round(world_y(want_h) * FX)
            got = mapdata.height_at(b, *mapdata.tile_centre(lx, lz), current=want_fx)
            if got is None or abs(got - want_fx) > tol:
                bad.append((wx, wz, want_h, None if got is None else (got / FX - 16.0) / TILE))
    return bad


def check_permissions(cid, raw):
    """Return [(x, z, want, got)] where permissions differ from layout."""
    cx, cz = layout.CHUNKS[cid]
    grid = layout.tiles()
    p = mapdata.read_permissions(raw)
    return [
        (cx * 32 + lx, cz * 32 + lz, grid[(cx * 32 + lx, cz * 32 + lz)][0], p[lz][lx])
        for lz in range(32)
        for lx in range(32)
        if p[lz][lx] != grid[(cx * 32 + lx, cz * 32 + lz)][0]
    ]


def main():
    failed = 0
    for cid in layout.CHUNKS:
        raw_bd = bdhc(cid)
        raw_perm = permissions(cid)
        b = mapdata.read_bdhc(raw_bd)
        off_h = check_bdhc(cid, raw_bd)
        off_p = check_permissions(cid, raw_perm)
        print(
            f"chunk {cid:03d}: {len(b['plates'])} plates, {len(b['strips'])} strips, {len(raw_bd)} B BDHC; "
            f"heights off: {len(off_h)}; permissions off: {len(off_p)}"
        )
        if off_h or off_p:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
