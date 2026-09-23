"""Bakes warm lava light into Mt. Coronet 1F South's vertex colours. See docs/coronet_1f_lava/PLAN.md, Step 5.

Usage: python3 tools/coronet_lava/tint_lava_glow.py  (safe to re-run)

The map's materials have lighting off, so area lights never reach the room: each vertex's COLOR command, multiplied by
its texture, is the whole of its shading. The stock mesh uses three greys, often one COLOR per shape. This rewrites
every shape's display list with a COLOR before each vertex, warmed by the vertex's distance to the nearest lava tile,
then re-lays out the model. The lava itself goes full white and the shore rim loses its stock cyan foam tint.

The untinted mesh is read from the branch point with main, so re-running never tints twice. The material dictionary
(renamed by add_lava_anim.py), perms and BDHC come from the current file.
"""
import math
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import nnsdict  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MAP_PATH = "res/field/maps/data/map_data_351.bin"
LAVA_MAT = "dun_sea_lm9"
SKIP_MATS = {"dun_light_lm1"}  # translucent light shaft at the exits
RIM_MAT = "dun_sside_lm8"

TILE = 1024  # raw vertex units per map tile
GRID = 32
RADIUS = 3.5  # tiles; warmth fades to nothing at this distance from lava
HEIGHT_FADE = 4.0  # tiles above the lava at which wall warmth is gone

# GX command parameter counts
NPARAMS = {0x00: 0, 0x10: 1, 0x11: 0, 0x12: 1, 0x13: 1, 0x14: 1, 0x15: 0, 0x16: 16, 0x17: 12, 0x18: 16, 0x19: 12,
           0x1A: 9, 0x1B: 3, 0x1C: 3, 0x20: 1, 0x21: 1, 0x22: 1, 0x23: 2, 0x24: 1, 0x25: 1, 0x26: 1, 0x27: 1,
           0x28: 1, 0x29: 1, 0x2A: 1, 0x2B: 1, 0x30: 1, 0x31: 1, 0x32: 1, 0x33: 1, 0x34: 32, 0x40: 1, 0x41: 0,
           0x50: 1, 0x60: 1, 0x70: 3, 0x71: 2, 0x72: 1}
COLOR, BEGIN = 0x20, 0x40
VTX = (0x23, 0x24, 0x25, 0x26, 0x27, 0x28)


def s(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def decode_dl(data):
    cmds, p = [], 0
    while p < len(data):
        ops = data[p:p + 4]
        p += 4
        for op in ops:
            n = NPARAMS[op]
            cmds.append((op, list(struct.unpack_from("<%dI" % n, data, p))))
            p += 4 * n
    return cmds


def encode_dl(cmds):
    cmds = [c for c in cmds if c[0] != 0x00]
    out = bytearray()
    for i in range(0, len(cmds), 4):
        group = cmds[i:i + 4]
        ops = [c[0] for c in group] + [0] * (4 - len(group))
        out += bytes(ops)
        for _, args in group:
            out += struct.pack("<%dI" % len(args), *args)
    return bytes(out)


def next_pos(op, args, pos):
    a = args[0]
    if op == 0x23:
        return [s(a & 0xFFFF, 16), s(a >> 16, 16), s(args[1] & 0xFFFF, 16)]
    if op == 0x24:
        return [s(a & 0x3FF, 10) << 6, s(a >> 10 & 0x3FF, 10) << 6, s(a >> 20 & 0x3FF, 10) << 6]
    if op == 0x25:
        return [s(a & 0xFFFF, 16), s(a >> 16, 16), pos[2]]
    if op == 0x26:
        return [s(a & 0xFFFF, 16), pos[1], s(a >> 16, 16)]
    if op == 0x27:
        return [pos[0], s(a & 0xFFFF, 16), s(a >> 16, 16)]
    return [pos[0] + s(a & 0x3FF, 10), pos[1] + s(a >> 10 & 0x3FF, 10), pos[2] + s(a >> 20 & 0x3FF, 10)]


def primitives(cmds):
    """Yields each polygon of a display list as a list of (x, y, z) vertices."""
    pos, kind, verts = [0, 0, 0], 0, []

    def flush():
        if kind == 0:
            return [verts[i:i + 3] for i in range(0, len(verts) - 2, 3)]
        if kind == 1:
            return [verts[i:i + 4] for i in range(0, len(verts) - 3, 4)]
        if kind == 2:
            return [verts[i:i + 3] for i in range(len(verts) - 2)]
        return [[verts[i], verts[i + 1], verts[i + 3], verts[i + 2]] for i in range(0, len(verts) - 3, 2)]

    for op, args in cmds:
        if op == BEGIN:
            yield from flush()
            kind, verts = args[0] & 3, []
        elif op in VTX:
            pos = next_pos(op, args, pos)
            verts.append(tuple(pos))
    yield from flush()


def inside(px, pz, poly):
    hit = False
    for i in range(len(poly)):
        (ax, _, az), (bx, _, bz) = poly[i], poly[i - 1]
        if (az > pz) != (bz > pz) and px < (bx - ax) * (pz - az) / (bz - az) + ax:
            hit = not hit
    return hit


def lava_tiles(lava_cmds):
    polys = list(primitives(lava_cmds))
    tiles, ys = set(), []
    for row in range(GRID):
        for col in range(GRID):
            cx, cz = (col - GRID / 2 + 0.5) * TILE, (row - GRID / 2 + 0.5) * TILE
            for poly in polys:
                if inside(cx, cz, poly):
                    tiles.add((col, row))
                    ys.append(sum(v[1] for v in poly) / len(poly))
                    break
    return tiles, min(ys)


def warmth(pos, tiles, lava_y):
    """0..1: how much lava light reaches a vertex."""
    x, y, z = pos[0] / TILE + GRID / 2, pos[1], pos[2] / TILE + GRID / 2
    best = RADIUS
    for col, row in tiles:
        dx = max(col - x, 0, x - col - 1)
        dz = max(row - z, 0, z - row - 1)
        best = min(best, math.hypot(dx, dz))
    w = (1 - best / RADIUS) ** 1.5
    return w * max(0.0, 1 - max(0, y - lava_y) / (HEIGHT_FADE * TILE))


def tint(grey, w):
    r = grey + (min(31, grey + 9) - grey) * w
    g = grey + (grey - 1 - grey) * w
    b = grey + (max(0, grey - 11) - grey) * w
    return round(r) | round(g) << 5 | round(b) << 10


def retint(cmds, mat, tiles, lava_y):
    out, pos, grey = [], [0, 0, 0], 25
    for op, args in cmds:
        if op == COLOR:
            c = args[0]
            grey = max(c & 31, c >> 5 & 31, c >> 10 & 31)  # the rim's cyan foam (0,31,31) becomes white
            continue
        if op in VTX:
            pos = next_pos(op, args, pos)
            if mat == LAVA_MAT:
                colour = 0x7FFF
            elif mat == RIM_MAT:
                colour = tint(grey, 1.0)
            else:
                colour = tint(grey, warmth(pos, tiles, lava_y))
            out.append((COLOR, [colour]))
        out.append((op, args))
    return out


class Model:
    def __init__(self, bmd):
        self.m = bytearray(bmd)
        m = self.m
        self.mdl0 = struct.unpack_from("<I", m, 16)[0]
        eb = self.mdl0 + 8 + struct.unpack_from("<H", m, self.mdl0 + 8 + 6)[0]
        self.mo = self.mdl0 + struct.unpack_from("<I", m, eb + 4)[0]
        size, sbc, mat, shp, evp = struct.unpack_from("<5I", m, self.mo)
        assert evp == size, "expected the envelope matrices to be empty"
        self.shp = self.mo + shp
        _, names, _ = nnsdict.parse(m, self.shp)
        seb = self.shp + struct.unpack_from("<H", m, self.shp + 6)[0]
        self.shapes = []  # (header offset, dl bytes)
        for i in range(len(names)):
            so = self.shp + struct.unpack_from("<I", m, seb + 4 + 4 * i)[0]
            _, _, _, odl, sdl = struct.unpack_from("<HHIII", m, so)
            self.shapes.append([so, bytes(m[so + odl:so + odl + sdl])])
        self.dl_start = min(so + struct.unpack_from("<I", m, so + 8)[0] for so, _ in self.shapes)
        assert self.dl_start >= max(so for so, _ in self.shapes) + 16
        self.mat_of_shape = self._bindings(sbc, mat)

    def _bindings(self, sbc, mat):
        m = self.m
        M = self.mo + mat
        _, mnames, _ = nnsdict.parse(m, M + 4)
        mnames = [n.rstrip(b"\0").decode() for n in mnames]
        nargs = {0: 0, 2: 2, 3: 1, 4: 1, 5: 1, 6: 3, 7: 1, 8: 1, 0xB: 0, 0xC: 2, 0xD: 2}
        p, cur, out = self.mo + sbc, None, {}
        while m[p] & 0x1F != 1:
            op = m[p]
            base = op & 0x1F
            if base == 4:
                cur = mnames[m[p + 1]]
            elif base == 5:
                out[m[p + 1]] = cur
            p += 1 + nargs[base] + ({1: 1, 2: 1, 3: 2}.get(op >> 5, 0) if base == 6 else 0)
        return out

    def rebuild(self):
        m = self.m[:self.dl_start]
        for so, dl in self.shapes:
            struct.pack_into("<II", m, so + 8, len(m) - so, len(dl))
            m += dl
        size = len(m) - self.mo
        struct.pack_into("<I", m, self.mo, size)
        struct.pack_into("<I", m, self.mo + 16, size)
        struct.pack_into("<I", m, self.mdl0 + 4, len(m) - self.mdl0)
        struct.pack_into("<I", m, 8, len(m))
        return bytes(m)


def split(d):
    sizes = struct.unpack_from("<4I", d, 0)
    parts, o = [], 16
    for n in sizes:
        parts.append(d[o:o + n])
        o += n
    assert o == len(d)
    return parts


def main():
    base_ref = subprocess.check_output(["git", "merge-base", "HEAD", "main"], cwd=ROOT, text=True).strip()
    stock = split(subprocess.check_output(["git", "show", f"{base_ref}:{MAP_PATH}"], cwd=ROOT))
    path = os.path.join(ROOT, MAP_PATH)
    with open(path, "rb") as f:
        cur = split(f.read())

    stock_model = Model(stock[2])
    model = Model(cur[2])
    assert len(stock_model.shapes) == len(model.shapes)
    # current dictionaries and headers (the material rename), stock display lists
    for i, shape in enumerate(model.shapes):
        shape[1] = stock_model.shapes[i][1]

    lava = next(i for i, mat in model.mat_of_shape.items() if mat == LAVA_MAT)
    tiles, lava_y = lava_tiles(decode_dl(model.shapes[lava][1]))
    print(f"{len(tiles)} lava tiles, lava plane y={lava_y:.0f}")

    for i, shape in enumerate(model.shapes):
        mat = model.mat_of_shape[i]
        if mat in SKIP_MATS:
            continue
        shape[1] = encode_dl(retint(decode_dl(shape[1]), mat, tiles, lava_y))

    cur[2] = model.rebuild()
    with open(path, "wb") as f:
        f.write(struct.pack("<4I", *map(len, cur)) + b"".join(cur))
    print(f"model {len(stock[2])} -> {len(cur[2])} bytes")


if __name__ == "__main__":
    main()
