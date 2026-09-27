#!/usr/bin/env python3
"""map_data_NNN.bin (land data) packer plus permissions, props and BDHC readers/writers. Standard library only.
See docs/lake_verity_redesign/pipeline.md and docs/maps/bdhc.md.

map_data layout: u32 permissions size (0x800), u32 props size, u32 NSBMD size, u32 BDHC size, then the four
sections in that order (land_data.c LandData_ReadHeader). Sections are stored uncompressed in the repo; the build
LZ10-compresses the model (tools/scripts/compress_land_data.py).

Permissions: 32 x 32 u16, row-major (z then x). Low byte = tile behaviour (collision value as used by layout.py:
WATER 0x15, GRASS 0x02, DOOR 0x6E ...), bit 15 = blocked (layout.py BLOCK 0x8000).

Props: 48-byte records {u32 model id (area_build list index -> build_model), VecFx32 position (relative to the chunk
centre), VecFx32 rotation (u16 angle units in fx32 slots), VecFx32 scale, u32 dummy[2]}.

BDHC: 'BDHC', u16 counts (points, normals, constants, plates, strips, access list), then points {fx32 x, z},
normals {fx32 x, y, z}, constants fx32, plates {u16 point1, point2, normal, constant}, strips {fx32 scanline,
u16 count, u16 first}, access list u16 plate indices. Coordinates are relative to the chunk centre (-256..256),
heights are world units (1 tile = 16).

Usage:
  python3 tools/lake_verity/mapdata.py info <map_data_NNN.bin>
  python3 tools/lake_verity/mapdata.py heights <map_data_NNN.bin>     (BDHC height at each tile centre, in tiles)
"""
import struct
import sys

FX = 4096
TILE = 16


# ---------------------------------------------------------------------------------------------------------------
# container
# ---------------------------------------------------------------------------------------------------------------

def unpack(data):
    """-> dict(permissions, props, model, bdhc) raw bytes."""
    sizes = struct.unpack_from("<4I", data)
    o, out = 16, {}
    for k, s in zip(("permissions", "props", "model", "bdhc"), sizes):
        out[k] = data[o:o + s]
        o += s
    assert o == len(data), (o, len(data))
    return out


def pack(permissions, props, model, bdhc):
    return struct.pack("<4I", len(permissions), len(props), len(model), len(bdhc)) + permissions + props + model + bdhc


# ---------------------------------------------------------------------------------------------------------------
# permissions
# ---------------------------------------------------------------------------------------------------------------

def read_permissions(raw):
    """-> 32 x 32 list [z][x] of u16."""
    v = struct.unpack("<1024H", raw)
    return [list(v[z * 32:(z + 1) * 32]) for z in range(32)]


def write_permissions(grid):
    return struct.pack("<1024H", *[grid[z][x] for z in range(32) for x in range(32)])


# ---------------------------------------------------------------------------------------------------------------
# props
# ---------------------------------------------------------------------------------------------------------------

PROP = struct.Struct("<I3i3i3i2I")


def read_props(raw):
    out = []
    for k in range(len(raw) // PROP.size):
        v = PROP.unpack_from(raw, k * PROP.size)
        out.append(dict(model=v[0], pos=list(v[1:4]), rot=list(v[4:7]), scale=list(v[7:10]), dummy=list(v[10:12])))
    return out


def write_props(props):
    return b"".join(PROP.pack(p["model"], *p["pos"], *p.get("rot", [0, 0, 0]), *p.get("scale", [FX, FX, FX]),
                              *p.get("dummy", [0, 0])) for p in props)


# ---------------------------------------------------------------------------------------------------------------
# BDHC
# ---------------------------------------------------------------------------------------------------------------

def read_bdhc(raw):
    assert raw[:4] == b"BDHC", raw[:4]
    npt, nn, nc, npl, ns, na = struct.unpack_from("<6H", raw, 4)
    o = 16
    pts = [struct.unpack_from("<2i", raw, o + 8 * i) for i in range(npt)]
    o += 8 * npt
    nrm = [struct.unpack_from("<3i", raw, o + 12 * i) for i in range(nn)]
    o += 12 * nn
    cst = list(struct.unpack_from("<%di" % nc, raw, o))
    o += 4 * nc
    plates = [struct.unpack_from("<4H", raw, o + 8 * i) for i in range(npl)]
    o += 8 * npl
    strips = [struct.unpack_from("<iHH", raw, o + 8 * i) for i in range(ns)]
    o += 8 * ns
    acc = list(struct.unpack_from("<%dH" % na, raw, o))
    o += 2 * na
    return dict(points=[list(p) for p in pts], normals=[list(n) for n in nrm], constants=cst,
                plates=[list(p) for p in plates], strips=[list(s) for s in strips], access=acc, tail=raw[o:])


def write_bdhc(b):
    out = b"BDHC" + struct.pack("<6H", len(b["points"]), len(b["normals"]), len(b["constants"]), len(b["plates"]),
                                len(b["strips"]), len(b["access"]))
    out += b"".join(struct.pack("<2i", *p) for p in b["points"])
    out += b"".join(struct.pack("<3i", *n) for n in b["normals"])
    out += struct.pack("<%di" % len(b["constants"]), *b["constants"])
    out += b"".join(struct.pack("<4H", *p) for p in b["plates"])
    out += b"".join(struct.pack("<iHH", *s) for s in b["strips"])
    out += struct.pack("<%dH" % len(b["access"]), *b["access"])
    return out + b.get("tail", b"")


def bdhc_plates(b):
    """-> [(x0, z0, x1, z1, normal, constant)] (fx32) in plate order."""
    out = []
    for p1, p2, ni, ci in b["plates"]:
        a, c = b["points"][p1], b["points"][p2]
        out.append((a[0], a[1], c[0], c[1], tuple(b["normals"][ni]), b["constants"][ci]))
    return out


def make_strips(plates_rect):
    """plates_rect: [(x0, z0, x1, z1)] -> (strips, access list). One strip per distinct plate z except the
    minimum; the strip (lo, hi] with scanline hi lists every plate with z_min <= hi and z_max > lo, in plate order.
    This reproduces the stock strips and access lists of 665 of the 666 stock BDHC files (the odd one has a
    zero-depth plate)."""
    zs = sorted({r[1] for r in plates_rect} | {r[3] for r in plates_rect})
    strips, acc = [], []
    for k in range(1, len(zs)):
        lo, hi = zs[k - 1], zs[k]
        lst = [i for i, r in enumerate(plates_rect) if min(r[1], r[3]) <= hi and max(r[1], r[3]) > lo]
        strips.append([hi, len(lst), len(acc)])
        acc += lst
    return strips, acc


def build_bdhc(plates):
    """plates: [(x0, z0, x1, z1, (nx, ny, nz), d)] fx32 -> BDHC dict with shared (deduplicated) points, normals and
    constants, and strips/access list derived with make_strips."""
    pts, nrm, cst = [], [], []

    def idx(lst, v):
        if v not in lst:
            lst.append(v)
        return lst.index(v)

    pl = []
    for x0, z0, x1, z1, n, d in plates:
        pl.append([idx(pts, (x0, z0)), idx(pts, (x1, z1)), idx(nrm, tuple(n)), idx(cst, d)])
    strips, acc = make_strips([p[:4] for p in plates])
    return dict(points=[list(p) for p in pts], normals=[list(n) for n in nrm], constants=cst, plates=pl,
                strips=strips, access=acc, tail=b"")


def fx_mul(a, b):
    return (a * b + 0x800) >> 12


def fx_div(a, b):
    """NitroSDK FX_Div: 64-bit (a << 32) / b on the hardware divider (truncating), then rounded to fx32."""
    q = abs(a << 32) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return (q + (1 << 19)) >> 20


def find_strip(strips, z):
    """Port of BDHC_FindStripIndexByScanline (bdhc.c)."""
    n = len(strips)
    if n == 0:
        return None
    if n == 1:
        return 0
    low, high = 0, n - 1
    mid = high // 2
    while True:
        if strips[mid][0] > z:
            if high - 1 > low:
                high = mid
                mid = (low + high) // 2
            else:
                return mid
        else:
            if low + 1 < high:
                low = mid
                mid = (low + high) // 2
            else:
                return mid + 1


def height_at(b, x, z, current=0):
    """Port of CalculateObjectHeight (bdhc.c): x, z, current in fx32, chunk-centred. Returns fx32 or None."""
    si = find_strip(b["strips"], z)
    if si is None:
        return None
    cnt, first = b["strips"][si][1], b["strips"][si][2]
    cands = []
    for i in range(cnt):
        p1, p2, ni, ci = b["plates"][b["access"][first + i]]
        a, c = b["points"][p1], b["points"][p2]
        if min(a[0], c[0]) <= x <= max(a[0], c[0]) and min(a[1], c[1]) <= z <= max(a[1], c[1]):
            n = b["normals"][ni]
            h = -(fx_mul(n[0], x) + fx_mul(n[2], z) + b["constants"][ci])
            cands.append(fx_div(h, n[1]))
            if len(cands) >= 10:
                break
    if not cands:
        return None
    return min(cands, key=lambda h: abs(h - current))  # first minimum wins, as in the C loop


def tile_centre(lx, lz):
    """Chunk-local tile (0..31) -> BDHC coordinates (fx32) of its centre."""
    return (lx * TILE + TILE // 2 - 256) * FX, (lz * TILE + TILE // 2 - 256) * FX


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    d = unpack(open(sys.argv[2], "rb").read())
    b = read_bdhc(d["bdhc"])
    if sys.argv[1] == "info":
        print({k: len(v) for k, v in d.items()})
        print("props:", read_props(d["props"]))
        print(f"bdhc: {len(b['points'])} points, {len(b['normals'])} normals, {len(b['constants'])} constants, "
              f"{len(b['plates'])} plates, {len(b['strips'])} strips, {len(b['access'])} access, tail {b['tail'].hex()}")
        for i, (x0, z0, x1, z1, n, c) in enumerate(bdhc_plates(b)):
            print(f"  plate {i:3d} x {x0 / FX:7.1f}..{x1 / FX:7.1f} z {z0 / FX:7.1f}..{z1 / FX:7.1f} "
                  f"n ({n[0] / FX:.3f}, {n[1] / FX:.3f}, {n[2] / FX:.3f}) d {c / FX:.3f}")
    elif sys.argv[1] == "heights":
        for lz in range(32):
            row = []
            for lx in range(32):
                h = height_at(b, *tile_centre(lx, lz))
                row.append("   ?" if h is None else f"{h / FX / TILE:4.1f}")
            print(" ".join(row))


if __name__ == "__main__":
    main()
