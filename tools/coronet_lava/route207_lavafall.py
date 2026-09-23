"""Adds a lava streak down the Mt. Coronet cliff beside the Route 207 cave entrance.

Usage: python3 tools/coronet_lava/route207_lavafall.py [--sheet]  (safe to re-run; needs numpy)
  --sheet also writes the texture frames to $OUT_DIR/lavafall.png (default /tmp/coronet_lava; needs Pillow).

Route 207's east chunk (map_data_026, texture set 007) has the Coronet 1F South entrance at local tile (21,8), in
the corner where the terraced south-facing ridge meets the terraced east cliff. The streak starts on the plateau
above, runs down the ridge's terraces one tile right of the cave and spreads into a small pool on the blocked
tile (22,7). Nothing walkable is covered.

Three pieces:
  texture   lavafall, 16x16 4bpp with colour 0 transparent: a molten ribbon with a crusted, wobbly edge. It and a
            16-colour palette are added to texture set 007, which only area 7 (Route 207) uses.
  geometry  a new material (unlit, white, both faces) and a new shape in map_data_026's model. The shape is a
            quad-strip ribbon draped over the terrain: each cross-section is raycast onto the stock mesh and
            lifted slightly along the surface normal. u runs across the ribbon, v along it by surface distance.
  animation a fldtanime entry that scrolls the texture down the ribbon one texel per frame.

The stock model and texture set are read from the branch point with main, so re-running never adds twice.
"""
import math
import os
import struct
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import add_lava_anim  # noqa: E402
import make_lava  # noqa: E402
import nnsdict  # noqa: E402
from tint_lava_glow import BEGIN, COLOR, decode_dl, encode_dl, primitives, split  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MAP_PATH = "res/field/maps/data/map_data_026.bin"
TEXSET_PATH = "res/field/maps/texture_sets/map_texture_set_007.nsbtx"

NAME = b"lavafall"
MAT_NAME = b"lavafall_lm1"
SHP_NAME = b"lavafall"
FRAME_VBLANKS = 5

TILE = 1024  # raw vertex units per map tile
GRID = 32
# decals and props that sit on top of the terrain; the ribbon drapes over the ground under them
SKIP_MATS = {"bridge_lm1", "hanger_lm4", "imped_lm1", "shadowchip_lm2"}

# centreline (local tile x, tile z), top to bottom; z only ever increases
PATH = [(23.30, 1.30), (23.05, 2.05), (22.80, 2.90), (22.95, 3.60), (22.60, 4.50), (22.40, 5.40), (22.58, 6.20),
        (22.52, 6.90), (22.62, 7.65)]
STEP = 1 / 8  # tiles between cross-sections; terrace edges sit on multiples of 1/4
HALF_WIDTH = 0.40  # tiles, sets the texel size
# (tile z, half width in tiles) keys, smoothly interpolated: a thin source, a pool on the wide ledge at height 3
# (rows 3-4, faces the camera), then down the lower terraces into the corner beside the cave
WIDTH = [(1.30, 0.03), (1.60, 0.28), (2.30, 0.36), (2.80, 0.42), (3.10, 0.62), (3.50, 0.72), (3.90, 0.62),
         (4.20, 0.38), (5.00, 0.36), (6.00, 0.40), (6.90, 0.40), (7.30, 0.46), (7.65, 0.12)]
LIFT = 20  # raw units along the surface normal
TEXELS_PER_TILE = 16 / (2 * HALF_WIDTH)  # square texels on the ribbon

# ---------------------------------------------------------------------------------------------------- texture

SIZE = 16
PALETTE = [(0, 0, 0),                                   # 0 transparent
           (58, 20, 16), (96, 30, 18),                  # 1-2 crust
           (150, 26, 10), (190, 36, 14), (222, 48, 15),  # 3-15 lava, dark red to white-hot
           (240, 70, 17), (246, 92, 19), (250, 116, 22), (252, 140, 28), (254, 164, 38), (255, 186, 56),
           (255, 206, 84), (255, 224, 124), (255, 242, 184), (255, 250, 220)]


def _texel(x, y):
    a = 2 * math.pi * y / SIZE
    hw = 6.2 + 0.9 * math.sin(a + 0.7) + 0.6 * math.sin(2 * a + 2.1)
    d = abs(x + 0.5 - SIZE / 2)
    if d > hw:
        return 0
    if d > hw - 1.1:
        return 1 if math.sin(3 * a + x) > 0.3 else 2
    t = d / hw
    heat = 0.70 - 0.55 * t * t
    heat += 0.22 * math.sin(2 * math.pi * x / 5.5 + 1.4 * math.sin(a + 0.3))
    heat += 0.18 * math.sin(2 * a + x * 0.8) + 0.12 * math.sin(3 * a - x * 1.3 + 1)
    return max(3, min(15, round(3 + heat * 12)))


def frames():
    """SIZE frames of SIZE rows x SIZE indices; frame f is the pattern moved f rows down the ribbon."""
    return [[[_texel(x, (y - f) % SIZE) for x in range(SIZE)] for y in range(SIZE)] for f in range(SIZE)]


# ---------------------------------------------------------------------------------------------------- texture set

def _dict_entries(d, o):
    _, names, _ = nnsdict.parse(d, o)
    eb = o + struct.unpack_from("<H", d, o + 6)[0]
    unit = struct.unpack_from("<H", d, eb)[0]
    return [n.rstrip(b"\0") for n in names], [bytes(d[eb + 4 + unit * i:eb + 4 + unit * (i + 1)])
                                              for i in range(len(names))]


def add_texture(nsbtx, name, texels, pal):
    """Returns nsbtx with a 16x16 colour-0-transparent 4bpp texture and a same-named palette appended."""
    t = struct.unpack_from("<I", nsbtx, 16)[0]
    assert struct.unpack_from("<H", nsbtx, 14)[0] == 1 and len(nsbtx) == t + struct.unpack_from("<I", nsbtx, t + 4)[0]
    u16 = lambda o: struct.unpack_from("<H", nsbtx, t + o)[0]  # noqa: E731
    u32 = lambda o: struct.unpack_from("<I", nsbtx, t + o)[0]  # noqa: E731
    assert u16(0x1C) == 0, "compressed textures are not handled"
    tex_names, tex_entries = _dict_entries(nsbtx, t + u16(0x0E))
    pal_names, pal_entries = _dict_entries(nsbtx, t + u16(0x34))
    tex_data = nsbtx[t + u32(0x14):t + u32(0x14) + (u16(0x0C) << 3)]
    pal_data = nsbtx[t + u32(0x38):t + u32(0x38) + (u16(0x30) << 3)]
    if name in tex_names or name in pal_names:
        raise ValueError(f"{name} is already in the texture set")

    param = add_lava_anim.TEX_PARAM | 1 << 29 | len(tex_data) >> 3
    tex_names.append(name)
    tex_entries.append(struct.pack("<II", param, add_lava_anim.TEX_EXTRA))
    pal_names.append(name)
    pal_entries.append(struct.pack("<HH", len(pal_data) >> 3, 0))
    tex_data += texels
    pal_data += b"".join(struct.pack("<H", make_lava.bgr555(c)) for c in pal)

    tex_dict = nnsdict.build(tex_names, tex_entries)
    pal_dict = nnsdict.build(pal_names, pal_entries)
    tex_dict_o = 0x3C
    pal_dict_o = tex_dict_o + len(tex_dict)
    tex_data_o = pal_dict_o + len(pal_dict)
    pal_data_o = tex_data_o + len(tex_data)
    size = pal_data_o + len(pal_data)
    tex0 = struct.pack("<4sII", b"TEX0", size, 0)
    tex0 += struct.pack("<HHII", len(tex_data) >> 3, tex_dict_o, 0, tex_data_o)
    tex0 += struct.pack("<IHHIII", 0, 0, tex_dict_o, 0, pal_data_o, pal_data_o)
    tex0 += struct.pack("<IHHII", 0, len(pal_data) >> 3, 0, pal_dict_o, pal_data_o)
    tex0 += tex_dict + pal_dict + tex_data + pal_data
    head = bytearray(nsbtx[:t])
    struct.pack_into("<I", head, 8, t + len(tex0))
    return bytes(head) + tex0


# ---------------------------------------------------------------------------------------------------- terrain

class Terrain:
    def __init__(self, polys):
        tris = [(p[0], p[k], p[k + 1]) for p in polys for k in range(1, len(p) - 1)]
        self.t = np.array(tris, dtype=float)
        a, b, c = self.t[:, 0], self.t[:, 1], self.t[:, 2]
        n = np.cross(b - a, c - a)
        n *= np.sign(n[:, 1:2] + 1e-9)  # upward
        n /= np.maximum(np.linalg.norm(n, axis=1), 1e-9)[:, None]
        keep = n[:, 1] > 1e-3  # walls can never be under a point
        self.t, self.n = self.t[keep], n[keep]

    def surface(self, x, z):
        """(y, normal) of the topmost terrain triangle over (x, z), in raw units."""
        a, b, c = self.t[:, 0], self.t[:, 1], self.t[:, 2]
        v0, v1 = c[:, [0, 2]] - a[:, [0, 2]], b[:, [0, 2]] - a[:, [0, 2]]
        v2 = np.array([x, z]) - a[:, [0, 2]]
        d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
        d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01
        with np.errstate(all="ignore"):
            u = (d11 * d20 - d01 * d21) / den
            v = (d00 * d21 - d01 * d20) / den
        hit = (u >= -1e-4) & (v >= -1e-4) & (u + v <= 1 + 1e-4)
        if not hit.any():
            raise ValueError(f"no terrain under ({x / TILE + GRID / 2:.2f}, {z / TILE + GRID / 2:.2f})")
        y = a[:, 1] + u * (c[:, 1] - a[:, 1]) + v * (b[:, 1] - a[:, 1])
        i = np.where(hit)[0][np.argmax(y[hit])]
        return y[i], self.n[i]


def centreline():
    """(x, z) in tiles every STEP of z, by Catmull-Rom through PATH."""
    pts = [PATH[0]] + PATH + [PATH[-1]]
    zs = np.arange(PATH[0][1], PATH[-1][1] + 1e-6, STEP)
    out = []
    for z in zs:
        k = max(i for i in range(1, len(pts) - 2) if pts[i][1] <= z + 1e-9) if z < PATH[-1][1] else len(pts) - 3
        p0, p1, p2, p3 = pts[k - 1], pts[k], pts[k + 1], pts[k + 2]
        s = (z - p1[1]) / (p2[1] - p1[1])
        x = 0.5 * (2 * p1[0] + (p2[0] - p0[0]) * s + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * s * s +
                   (3 * p1[0] - p0[0] - 3 * p2[0] + p3[0]) * s ** 3)
        out.append((x, z))
    return out


def half_width(z):
    for (z0, w0), (z1, w1) in zip(WIDTH, WIDTH[1:]):
        if z <= z1:
            u = min(1.0, max(0.0, (z - z0) / (z1 - z0)))
            return w0 + (w1 - w0) * u * u * (3 - 2 * u)
    return WIDTH[-1][1]


def ribbon(terrain):
    """Rows of (x, y, z, s, t): three vertices per cross-section, raw units and 1/16 texels."""
    rows, t, prev = [], 0.0, None
    for cx, cz in centreline():
        _, n = terrain.surface((cx - GRID / 2) * TILE, (cz - GRID / 2) * TILE)
        hw = half_width(cz) * (0.85 + 0.3 * n[1] ** 2)  # spreads on the ledges, narrows down the drops
        row = []
        for k, off in enumerate((-hw, 0.0, hw)):
            x, z = (cx + off - GRID / 2) * TILE, (cz - GRID / 2) * TILE
            y, n = terrain.surface(x, z)
            p = np.array([x, y, z]) + n * LIFT
            row.append(p)
        if prev is not None:
            t += np.linalg.norm(row[1] - prev) / TILE * TEXELS_PER_TILE
        prev = row[1]
        rows.append([(p[0], p[1], p[2], k * 8 * 16, t * 16) for k, p in enumerate(row)])
    return rows


def ribbon_dl(rows):
    def texcoord(s, t):
        return 0x22, [(round(s) & 0xFFFF) | (round(t) & 0xFFFF) << 16]

    def vtx(x, y, z):
        x, y, z = (int(round(v)) for v in (x, y, z))
        assert all(-0x8000 <= v < 0x8000 for v in (x, y, z))
        return 0x23, [(x & 0xFFFF) | (y & 0xFFFF) << 16, z & 0xFFFF]

    cmds = [(COLOR, [0x7FFF])]
    for band in ((0, 1), (1, 2)):
        cmds.append((BEGIN, [3]))  # quad strip
        for row in rows:
            for k in band:
                x, y, z, s, t = row[k]
                cmds += [texcoord(s, t), vtx(x, y, z)]
        cmds.append((0x41, []))
    return encode_dl(cmds)


# ---------------------------------------------------------------------------------------------------- model

def _pad4(b):
    return b + b"\0" * (-len(b) % 4)


class Mdl:
    """The one model of a map NSBMD, split into the parts this script changes."""

    def __init__(self, bmd):
        self.bmd = bytes(bmd)
        m = self.bmd
        self.mdl0 = struct.unpack_from("<I", m, 16)[0]
        eb = self.mdl0 + 8 + struct.unpack_from("<H", m, self.mdl0 + 8 + 6)[0]
        self.mo = self.mdl0 + struct.unpack_from("<I", m, eb + 4)[0]
        size, sbc, mat, shp, evp = struct.unpack_from("<5I", m, self.mo)
        assert evp == size and self.mo + size == len(m), "expected one model, no envelopes, nothing after it"
        mo = self.mo
        self.head = bytearray(m[mo + 20:mo + sbc])  # model info and node data
        self.sbc = bytes(m[mo + sbc:mo + mat])

        M = mo + mat
        tex_o, pal_o = struct.unpack_from("<HH", m, M)
        names, entries = _dict_entries(m, M + 4)
        self.mat_names = names
        self.mats = []
        for e in entries:
            o = M + struct.unpack_from("<I", e)[0]
            self.mats.append(bytes(m[o:o + struct.unpack_from("<H", m, o + 2)[0]]))
        self.bind = []
        for o in (tex_o, pal_o):
            names, entries = _dict_entries(m, M + o)
            lists = []
            for e in entries:
                lo, count, flag = struct.unpack("<HBB", e)
                lists.append((list(m[M + lo:M + lo + count]), flag))
            self.bind.append([names, lists])

        S = mo + shp
        names, entries = _dict_entries(m, S)
        self.shp_names = names
        self.shapes = []  # (header without the display list fields, display list)
        for e in entries:
            so = S + struct.unpack_from("<I", e)[0]
            tag, size, flag, odl, sdl = struct.unpack_from("<HHIII", m, so)
            self.shapes.append([(tag, size, flag), bytes(m[so + odl:so + odl + sdl])])

    def material_index(self, name):
        return self.mat_names.index(name)

    def add_material(self, name, data, tex, pal):
        idx = len(self.mat_names)
        self.mat_names.append(name)
        self.mats.append(data)
        for (names, lists), key in zip(self.bind, (tex, pal)):
            if key in names:
                lists[names.index(key)][0].append(idx)
            else:
                names.append(key)
                lists.append(([idx], 0))
        return idx

    def add_shape(self, name, flag, dl):
        self.shp_names.append(name)
        self.shapes.append([(0, 16, flag), dl])
        return len(self.shapes) - 1

    def draw(self, mat, shp):
        """Appends MAT/SHP to the draw sequence, before the trailing inverse POSSCALE and RET."""
        tail = self.sbc.rindex(b"\x2b\x01")
        self.sbc = self.sbc[:tail] + bytes((0x04, mat, 0x05, shp)) + self.sbc[tail:]

    def _mat_block(self):
        dicts = [None, None, None]

        def layout():
            o = 4 + sum(len(d) for d in dicts)
            list_offs = []
            blob = b""
            for names, lists in self.bind:
                offs = []
                for idxs, _ in lists:
                    offs.append(o + len(blob))
                    blob += bytes(idxs)
                list_offs.append(offs)
            blob = _pad4(blob)
            mat_offs, mats = [], b""
            for data in self.mats:
                mat_offs.append(o + len(blob) + len(mats))
                mats += _pad4(data)
            return list_offs, mat_offs, blob + mats

        # dictionary sizes do not depend on their entries, so lay out once with placeholders
        dicts[0] = nnsdict.build(self.mat_names, [b"\0" * 4] * len(self.mat_names))
        for i, (names, _) in enumerate(self.bind):
            dicts[i + 1] = nnsdict.build(names, [b"\0" * 4] * len(names))
        list_offs, mat_offs, tail = layout()
        dicts[0] = nnsdict.build(self.mat_names, [struct.pack("<I", o) for o in mat_offs])
        for i, (names, lists) in enumerate(self.bind):
            dicts[i + 1] = nnsdict.build(names, [struct.pack("<HBB", o, len(idxs), flag)
                                                 for o, (idxs, flag) in zip(list_offs[i], lists)])
        head = struct.pack("<HH", 4 + len(dicts[0]), 4 + len(dicts[0]) + len(dicts[1]))
        return head + b"".join(dicts) + tail

    def _shp_block(self):
        n = len(self.shapes)
        dict_len = len(nnsdict.build(self.shp_names, [b"\0" * 4] * n))
        hdr0 = _pad4(b"\0" * dict_len)
        hdr0 = len(hdr0)
        headers, dls = b"", b""
        dl0 = hdr0 + 16 * n
        for i, ((tag, size, flag), dl) in enumerate(self.shapes):
            so = hdr0 + 16 * i
            headers += struct.pack("<HHIII", tag, size, flag, dl0 + len(dls) - so, len(dl))
            dls += _pad4(dl)
        d = nnsdict.build(self.shp_names, [struct.pack("<I", hdr0 + 16 * i) for i in range(n)])
        return _pad4(d) + headers + dls

    def build(self):
        head = bytearray(self.head)
        head[4], head[5] = len(self.mats), len(self.shapes)  # numMat, numShp
        sbc = _pad4(self.sbc)
        mat = self._mat_block()
        shp = self._shp_block()
        o_sbc = 20 + len(head)
        o_mat = o_sbc + len(sbc)
        o_shp = o_mat + len(mat)
        size = o_shp + len(shp)
        model = struct.pack("<5I", size, o_sbc, o_mat, o_shp, size) + head + sbc + mat + shp
        out = bytearray(self.bmd[:self.mo]) + model
        struct.pack_into("<I", out, self.mdl0 + 4, len(out) - self.mdl0)
        struct.pack_into("<I", out, 8, len(out))
        return bytes(out)


def lava_material(template):
    """The template material, unlit and white, drawn from both sides."""
    m = bytearray(template)
    struct.pack_into("<I", m, 4, 0x7FFF7FFF | 0x8000)  # diffuse white, set as vertex colour; ambient white
    poly = struct.unpack_from("<I", m, 12)[0]
    struct.pack_into("<I", m, 12, (poly & ~0xCF) | 0xC0)  # lights off, front and back faces
    struct.pack_into("<HH", m, 0x20, SIZE, SIZE)  # original width and height
    return bytes(m)


def terrain_polys(mdl):
    polys = []
    for i, (_, dl) in enumerate(mdl.shapes):
        mat = next((mdl.mat_names[m] for m, s in _draws(mdl.sbc) if s == i), None)
        if mat is None or mat.decode() in SKIP_MATS:
            continue
        polys += list(primitives(decode_dl(dl)))
    return polys


def _draws(sbc):
    """(material, shape) pairs in draw order."""
    nargs = {0: 0, 2: 2, 3: 1, 4: 1, 5: 1, 6: 3, 7: 1, 8: 1, 0xB: 0, 0xC: 2, 0xD: 2}
    out, cur, p = [], None, 0
    while sbc[p] & 0x1F != 1:
        op = sbc[p] & 0x1F
        if op == 4:
            cur = sbc[p + 1]
        elif op == 5:
            out.append((cur, sbc[p + 1]))
        p += 1 + nargs[op] + ({1: 1, 2: 1, 3: 2}.get(sbc[p] >> 5, 0) if op == 6 else 0)
    return out


# ---------------------------------------------------------------------------------------------------- main

def stock(path):
    base = subprocess.check_output(["git", "merge-base", "HEAD", "main"], cwd=ROOT, text=True).strip()
    return subprocess.check_output(["git", "show", f"{base}:{path}"], cwd=ROOT)


def main():
    art = frames()
    texset = add_texture(stock(TEXSET_PATH), NAME, make_lava.texels_4bpp(art[0]), PALETTE)
    with open(os.path.join(ROOT, TEXSET_PATH), "wb") as f:
        f.write(texset)

    parts = split(stock(MAP_PATH))
    mdl = Mdl(parts[2])
    terrain = Terrain(terrain_polys(mdl))
    rows = ribbon(terrain)
    template = mdl.mats[mdl.material_index(b"criff_lm38")]
    mat = mdl.add_material(MAT_NAME, lava_material(template), NAME, NAME)
    shp = mdl.add_shape(SHP_NAME, 0x6, ribbon_dl(rows))  # uses colour and texcoords
    mdl.draw(mat, shp)
    parts[2] = mdl.build()
    with open(os.path.join(ROOT, MAP_PATH), "wb") as f:
        f.write(struct.pack("<4I", *map(len, parts)) + b"".join(parts))

    idx = add_lava_anim.update_fldtanime(NAME, art, PALETTE, FRAME_VBLANKS)
    print(f"{len(rows)} cross-sections, {2 * (len(rows) - 1)} quads; fldtanime entry {idx} = {NAME.decode()}")

    if "--sheet" in sys.argv:
        from PIL import Image

        out_dir = os.environ.get("OUT_DIR", "/tmp/coronet_lava")
        os.makedirs(out_dir, exist_ok=True)
        im = Image.new("RGB", (SIZE * len(art), SIZE))
        for i, fr in enumerate(art):
            for y, r in enumerate(fr):
                for x, v in enumerate(r):
                    im.putpixel((i * SIZE + x, y), (40, 90, 40) if v == 0 else PALETTE[v])
        im.resize((im.width * 8, im.height * 8), Image.NEAREST).save(os.path.join(out_dir, "lavafall.png"))


if __name__ == "__main__":
    main()
