#!/usr/bin/env python3
"""Shared helpers for the Arc 2 world-art map edits (Route 212 North gate, Solaceon wall, Veilstone shrine).

Standard library only. Builds on the Lake Verity pipeline (tools/lake_verity: nsbmd.py, nsbtx.py, mapdata.py) and the
Route 203 scar's approach (tools/route_203), with one difference: the chunk model is edited in place instead of being
rebuilt from a mesh. Stock shapes that the edit does not cut keep their display lists and stock materials byte for
byte; only the shapes that lose faces are re-encoded, and the new geometry is appended as new materials and shapes.
That keeps every non-standard stock material attribute (polygon ids, translucent shadows, diffuse values) intact.

  ChunkEdit(rel, chunk_xy, base_rev)   the stock chunk at base_rev (read from git, so re-running never feeds back)
      .drop(pred)                      drop stock faces: pred(texture, palette, centroid (x, h, z), face) -> bool
      .clip_flat(textures, rects)      cut axis-aligned flat faces of these textures by rectangles (kept outside)
      .add(mesh_builder)               append new geometry (materials + shapes)
      .model_bytes()                   the NSBMD
      .pack(perm)                      the map_data bin (stock props and BDHC, these permissions)
  MeshBuilder                          new faces per material, absolute tiles (x, h, z), explicit flat normals
  texset_append(...)                   append textures/palettes to a stock texture set, asserting stock is unchanged

Coordinates: absolute tiles x/z (matrix-global), h in tiles where the field ground of the overworld chunks is h 1.0
(world y 32; nsbmd.GROUND_Y + 16 * h).
"""
import math
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402

MODEL_BUFFER = 0xF000      # land_data.c map model load buffer, per chunk (uncompressed)
VRAM_PROVEN = 76416        # largest stock map texture set (048)


def git_file(rev, rel):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True, capture_output=True).stdout


# ---------------------------------------------------------------------------------------------------------------
# texture sets
# ---------------------------------------------------------------------------------------------------------------

def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def ramp(keys, t):
    t = max(0.0, min(1.0, t))
    n = len(keys) - 1
    i = min(int(t * n), n - 1)
    f = t * n - i
    return tuple(round(keys[i][k] + (keys[i + 1][k] - keys[i][k]) * f) for k in range(3))


def used_indices(tx):
    _, idx = nsbtx.decode(tx, [0] * 256)
    return sorted({v for row in idx for v in row})


def recolour(src_colors, used, keys, keep=()):
    """Each stock colour mapped onto the ramp `keys` by luminance (normalised over the colours the texture uses);
    indices in `keep` keep their stock value (e.g. a transparent colour 0)."""
    rgbs = [nsbtx.rgb(c) for c in src_colors]
    ls = [lum(rgbs[i]) for i in used if i < len(rgbs)]
    lo, hi = min(ls), max(ls)
    out = []
    for i, c in enumerate(rgbs):
        if i in keep:
            out.append(src_colors[i])
            continue
        t = (lum(c) - lo) / (hi - lo) if hi > lo else 0.5
        out.append(nsbtx.bgr555(ramp(keys, t)))
    return out


def indexed_texture(name, idx, pal, c0=1):
    """32x32 (or any size) pltt16 texture from an index grid; colour 0 transparent when c0."""
    h, w = len(idx), len(idx[0])
    flat = [v for row in idx for v in row]
    data = bytearray()
    for i in range(0, len(flat), 2):
        data.append(flat[i] | flat[i + 1] << 4)
    tex = dict(name=name, fmt=3, w=w, h=h, c0=c0, data=bytes(data))
    cols = [nsbtx.bgr555(c) for c in pal] + [0] * (16 - len(pal))
    return tex, dict(name=name + "_pl", colors=cols[:16], pltt4=0)


def texset_append(set_rel, base_rev, recolours=(), new_textures=(), new_palettes=()):
    """Stock set at base_rev + new entries. recolours: [(palette name, texture, stock palette, ramp, keep)].
    Returns (base bytes, new bytes, report str). Asserts: no name clash, stock textures and palettes unchanged,
    VRAM within the largest stock set."""
    base = git_file(base_rev, set_rel)
    s = nsbtx.parse(base)
    T = {t["name"]: t for t in s["textures"]}
    P = {p["name"]: p for p in s["palettes"]}
    pals = list(new_palettes)
    for name, tex, pal, keys, keep in recolours:
        pals.append(dict(name=name, colors=recolour(P[pal]["colors"], used_indices(T[tex]), keys, keep), pltt4=0))
    texs = list(new_textures)
    names = set(T) | set(P)
    clash = [e["name"] for e in texs + pals if e["name"] in names]
    assert not clash, f"name clash with stock entries: {clash}"
    assert all(len(e["name"]) <= 16 for e in texs + pals)
    for t in s["textures"]:
        t.pop("off", None)
    for p in s["palettes"]:
        p.pop("off", None)
    out = nsbtx.build(s["textures"] + texs, s["palettes"] + pals, pal_flag=s["header"]["pal_flag"])
    sb, so = nsbtx.parse(base), nsbtx.parse(out)
    OT = {t["name"]: t for t in so["textures"]}
    OP = {p["name"]: p for p in so["palettes"]}
    for t in sb["textures"]:
        t2 = OT[t["name"]]
        assert t2["data"] == t["data"] and (t2["fmt"], t2["w"], t2["h"], t2["c0"]) == (t["fmt"], t["w"], t["h"], t["c0"])
    for p in sb["palettes"]:
        assert OP[p["name"]]["data"].startswith(p["data"]), p["name"]
    vb, vo = nsbtx.vram_usage(sb), nsbtx.vram_usage(so)
    assert sum(vo) <= VRAM_PROVEN, sum(vo)
    rep = (f"{set_rel}: {len(sb['textures'])} -> {len(so['textures'])} textures, {len(sb['palettes'])} -> "
           f"{len(so['palettes'])} palettes; VRAM {sum(vb)} -> {sum(vo)} B (texels {vb[0]} -> {vo[0]}, palettes "
           f"{vb[1]} -> {vo[1]}); stock textures and palettes unchanged")
    return base, out, rep


def texture_table(set_bytes):
    s = nsbtx.parse(set_bytes)
    return {t["name"]: {"size": [t["w"], t["h"]]} for t in s["textures"]}, {p["name"] for p in s["palettes"]}


# ---------------------------------------------------------------------------------------------------------------
# new geometry
# ---------------------------------------------------------------------------------------------------------------

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def face_normal(pts):
    """Outward normal of a face wound like the stock map faces (counter-clockwise seen from the front), positions
    (x, h, z): a ground quad (x0,z1) (x1,z1) (x1,z0) (x0,z0) gives +h, a south wall gives +z."""
    n = _cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0]))
    if len(pts) == 4 and sum(c * c for c in n) < 1e-12:
        n = _cross(_sub(pts[2], pts[0]), _sub(pts[3], pts[0]))
    return _norm(n)


class MeshBuilder:
    """Faces per material (absolute tiles), with flat per-face normals so edges stay crisp."""

    def __init__(self):
        self.materials = {}
        self.meshes = {}

    def material(self, name, texture, palette, size, lights=1, cull="back", alpha=31, polygon_id=0, fog=True,
                 repeat=(True, True), flip=(False, False)):
        assert len(name) <= 16, name
        self.materials.setdefault(name, dict(name=name, texture=texture, palette=palette, size=list(size),
                                             polygon_attr=dict(lights=lights, cull=cull, fog=fog,
                                                               polygon_id=polygon_id),
                                             alpha=alpha, repeat=list(repeat), flip=list(flip)))
        self.meshes.setdefault(name, dict(material=name, positions=[], uvs=[], colors=[], normals=[], quads=[],
                                          tris=[]))
        return name

    def face(self, mat, pts, uvs, color=(255, 255, 255)):
        me = self.meshes[mat]
        n = face_normal(pts)
        b = len(me["positions"])
        me["positions"] += [list(p) for p in pts]
        me["uvs"] += [list(u) for u in uvs]
        me["colors"] += [list(color)] * len(pts)
        me["normals"] += [list(n)] * len(pts)
        (me["quads"] if len(pts) == 4 else me["tris"]).append(list(range(b, b + len(pts))))

    def flat(self, mat, x0, z0, x1, z1, h, uv_per_tile=1.0, uv0=(0, 0)):
        """Horizontal quad visible from above, UVs planar (u along x, v along z)."""
        pts = [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)]
        uvs = [((p[0] - x0) * uv_per_tile + uv0[0], (p[2] - z0) * uv_per_tile + uv0[1]) for p in pts]
        self.face(mat, pts, uvs)

    def mesh(self, name="new"):
        return {"name": name, "materials": list(self.materials.values()),
                "meshes": [m for m in self.meshes.values() if m["quads"] or m["tris"]]}

    def polygons(self):
        return sum(len(m["quads"]) + len(m["tris"]) for m in self.meshes.values())


# ---------------------------------------------------------------------------------------------------------------
# the stock chunk, edited in place
# ---------------------------------------------------------------------------------------------------------------

class ChunkEdit:
    def __init__(self, rel, chunk_xy, base_rev):
        self.rel = rel
        self.cx, self.cz = chunk_xy
        self.sec = mapdata.unpack(git_file(base_rev, rel))
        bmd = nsbmd.parse_bmd(self.sec["model"])
        assert len(bmd["models"]) == 1
        self.model = bmd["models"][0]
        self.ps = self.model["info"]["pos_scale"] / nsbmd.FX
        self.stock_stats = nsbmd.model_stats(self.model)
        self.pairs = nsbmd.shape_material_pairs(self.model)
        self.shape_mat = {si: mi for mi, si in self.pairs}
        # per shape: decoded faces (only filled for shapes that get edited)
        self.faces = {}
        self.dropped = 0
        self.clipped = 0
        self.new = []

    # -- coordinates
    def tile(self, pos):
        """fx16 vertex -> absolute tiles (x, h, z)."""
        wx, wy, wz = (c * self.ps / nsbmd.FX for c in pos)
        return (wx / nsbmd.TILE + 16 + self.cx * 32, (wy - nsbmd.GROUND_Y) / nsbmd.TILE,
                wz / nsbmd.TILE + 16 + self.cz * 32)

    def fx(self, t):
        x, h, z = t
        w = ((x - self.cx * 32 - 16) * nsbmd.TILE, nsbmd.GROUND_Y + h * nsbmd.TILE, (z - self.cz * 32 - 16) * nsbmd.TILE)
        return tuple(round(c / self.ps * nsbmd.FX) for c in w)

    def material_of(self, si):
        return self.model["materials"][self.shape_mat[si]]

    def _faces(self, si):
        if si not in self.faces:
            prims = nsbmd.dl_primitives(nsbmd.dl_decode(self.model["shapes"][si]["dl"]))
            tris, quads = nsbmd.prims_to_faces(prims)
            self.faces[si] = (list(tris), list(quads))
        return self.faces[si]

    def iter_shapes(self):
        for si in range(len(self.model["shapes"])):
            m = self.material_of(si)
            yield si, m["texture"], m["palette"]

    def drop(self, pred, textures=None):
        """Drop stock faces for which pred(texture, palette, centroid, tile_pts) is true."""
        for si, tex, pal in self.iter_shapes():
            if textures is not None and tex not in textures:
                continue
            tris, quads = self._faces(si)
            keep_t, keep_q = [], []
            for lst, keep in ((tris, keep_t), (quads, keep_q)):
                for f in lst:
                    pts = [self.tile(v["pos"]) for v in f]
                    c = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
                    if pred(tex, pal, c, pts):
                        self.dropped += 1
                    else:
                        keep.append(f)
            if len(keep_t) == len(tris) and len(keep_q) == len(quads):
                del self.faces[si]            # nothing dropped: the shape stays byte-identical
            else:
                self.faces[si] = (keep_t, keep_q)

    def clip_flat(self, textures, rects):
        """Axis-aligned horizontal quads of these textures lose the parts inside the rectangles [x0,x1) x [z0,z1)
        (absolute tiles); the rest is kept with bilinearly interpolated UVs (exact for these affine quads). Faces that
        are not flat axis-aligned quads and whose centroid is inside a rectangle are dropped."""
        for si, tex, pal in self.iter_shapes():
            if tex not in textures:
                continue
            tris, quads = self._faces(si)
            out_q, out_t = [], []
            for f in quads:
                pieces = [f]
                for r in rects:
                    nxt = []
                    for q in pieces:
                        nxt += self._clip_quad(q, r)
                    pieces = nxt
                if len(pieces) != 1 or pieces[0] is not f:
                    self.clipped += 1
                out_q += pieces
            for f in tris:
                pts = [self.tile(v["pos"]) for v in f]
                c = tuple(sum(p[k] for p in pts) / 3 for k in range(3))
                if any(r[0] <= c[0] < r[2] and r[1] <= c[2] < r[3] for r in rects):
                    self.dropped += 1
                else:
                    out_t.append(f)
            if out_t == list(tris) and len(out_q) == len(quads) and all(a is b for a, b in zip(out_q, quads)):
                del self.faces[si]
            else:
                self.faces[si] = (out_t, out_q)

    def _clip_quad(self, f, r):
        pts = [self.tile(v["pos"]) for v in f]
        xs = sorted({round(p[0], 4) for p in pts})
        zs = sorted({round(p[2], 4) for p in pts})
        hs = {round(p[1], 4) for p in pts}
        rx0, rz0, rx1, rz1 = r
        if len(xs) != 2 or len(zs) != 2 or len(hs) != 1:
            c = tuple(sum(p[k] for p in pts) / 4 for k in range(3))
            if rx0 <= c[0] < rx1 and rz0 <= c[2] < rz1:
                self.dropped += 1
                return []
            return [f]
        (ax, bx), (az, bz) = xs, zs
        ix0, iz0, ix1, iz1 = max(ax, rx0), max(az, rz0), min(bx, rx1), min(bz, rz1)
        if ix0 >= ix1 or iz0 >= iz1:
            return [f]

        def corner(x, z):
            for p, v in zip(pts, f):
                if abs(p[0] - x) < 1e-3 and abs(p[2] - z) < 1e-3:
                    return v
            raise AssertionError("corner")
        v00, v10, v01 = corner(ax, az), corner(bx, az), corner(ax, bz)

        def vert(x, z):
            fx_, fz_ = (x - ax) / (bx - ax), (z - az) / (bz - az)
            uv = tuple(round(v00["uv"][k] + (v10["uv"][k] - v00["uv"][k]) * fx_ + (v01["uv"][k] - v00["uv"][k]) * fz_)
                       for k in range(2))
            return {"pos": self.fx((x, pts[0][1], z)), "uv": uv, "color": v00["color"], "normal": v00["normal"]}
        parts = []
        if az < iz0:
            parts.append((ax, az, bx, iz0))
        if iz1 < bz:
            parts.append((ax, iz1, bx, bz))
        if ax < ix0:
            parts.append((ax, iz0, ix0, iz1))
        if ix1 < bx:
            parts.append((ix1, iz0, bx, iz1))
        out = []
        for x0, z0, x1, z1 in parts:
            out.append((vert(x0, z1), vert(x1, z1), vert(x1, z0), vert(x0, z0)))
        return out

    def add(self, mb, textures):
        self.new.append((mb, textures))

    # -- assembly
    def build_model(self):
        m = self.model
        materials = list(m["materials"])
        shapes = []
        for si, s in enumerate(m["shapes"]):
            if si in self.faces:
                tris, quads = self.faces[si]
                if not tris and not quads:
                    # keep an empty-but-valid shape (one degenerate-free empty list is not encodable): mark for removal
                    shapes.append(None)
                    continue
                prims = nsbmd.faces_to_prims(tris, quads)
                cmds = nsbmd.encode_prims(prims, use_color=False, use_uv=True, use_normal=True)
                s = dict(s, dl=nsbmd.dl_pack(cmds))
            shapes.append(s)
        draw = [(mi, si) for mi, si in self.pairs if shapes[si] is not None]
        # drop emptied shapes, renumber
        remap, kept = {}, []
        for si, s in enumerate(shapes):
            if s is not None:
                remap[si] = len(kept)
                kept.append(s)
        draw = [(mi, remap[si]) for mi, si in draw]
        n_stock = len(kept)
        for mb, textures in self.new:
            mesh = mb.mesh()
            if not mesh["meshes"]:
                continue
            sub = nsbmd.mesh_to_model(mesh, (self.cx, self.cz), name="x", textures=textures,
                                      pos_scale=m["info"]["pos_scale"])
            for k, (mat, shp) in enumerate(zip(sub["materials"], sub["shapes"])):
                assert mat["name"] not in {x["name"] for x in materials}, mat["name"]
                materials.append(mat)
                kept.append(dict(shp, name=f"polygon{len(kept)}"))
                draw.append((len(materials) - 1, len(kept) - 1))
        # names of re-numbered stock shapes stay as they were unless they collide
        names = set()
        for i, s in enumerate(kept):
            if s["name"] in names:
                s["name"] = f"polygon{i}x"
            names.add(s["name"])

        def binds(key, stock):
            """Stock bind entries keep their order, lists and flags; new names are appended (NNS looks them up
            through the dictionary, so the order is not significant)."""
            out = [dict(b, mats=list(b["mats"])) for b in stock]
            by = {b["name"]: b for b in out}
            for i in range(len(m["materials"]), len(materials)):
                n = materials[i][key]
                if n not in by:
                    by[n] = {"name": n, "mats": [], "flag": 0}
                    out.append(by[n])
                by[n]["mats"].append(i)
            return out
        sbc = [c for c in m["sbc"] if not (bytes.fromhex(c)[0] & 0x1F) in (0x04, 0x05)]
        # stock layout: 26.., 02.., 0b, [04 mi, 05 si]*, 2b, 01
        head = sbc[:sbc.index("0b") + 1]
        tail = sbc[sbc.index("0b") + 1:]
        body = []
        for mi, si in draw:
            body += ["04%02x" % mi, "05%02x" % si]
        assert len(materials) < 256 and len(kept) < 256
        new = dict(m, materials=materials, shapes=kept, sbc=head + body + tail, sbc_pad=None,
                   tex_bind=binds("texture", m["tex_bind"]), pltt_bind=binds("palette", m["pltt_bind"]))
        st = nsbmd.model_stats(new)
        allpos = []          # only the new shapes can grow the box (cut stock shapes are subsets of stock)
        for s in kept[n_stock:]:
            for t, vs in nsbmd.dl_primitives(nsbmd.dl_decode(s["dl"])):
                allpos += [v["pos"] for v in vs]
        info = dict(m["info"])
        k = info["box_pos_scale"] // info["pos_scale"]
        mn = [min([p[i] for p in allpos] or [1 << 30]) for i in range(3)]
        mx = [max([p[i] for p in allpos] or [-(1 << 30)]) for i in range(3)]
        sb = [info["box_x"], info["box_y"], info["box_z"]]
        se = [info["box_x"] + info["box_w"], info["box_y"] + info["box_h"], info["box_z"] + info["box_d"]]
        lo = [min(sb[i], mn[i] // k) for i in range(3)]
        hi = [max(se[i], -(-mx[i] // k)) for i in range(3)]
        info.update(num_mat=len(materials), num_shp=len(kept), num_vertex=st["vertices_sent"],
                    num_polygon=st["polygons"], num_triangle=st["triangles"], num_quad=st["quads"],
                    box_x=lo[0], box_y=lo[1], box_z=lo[2], box_w=hi[0] - lo[0], box_h=hi[1] - lo[1],
                    box_d=hi[2] - lo[2])
        new["info"] = info
        return new

    def model_bytes(self):
        self.built = self.build_model()
        return nsbmd.build_bmd([self.built])

    def permissions(self):
        return mapdata.read_permissions(self.sec["permissions"])

    def pack(self, perm, model_bytes):
        return mapdata.pack(mapdata.write_permissions(perm), self.sec["props"], model_bytes, self.sec["bdhc"])

    def stats(self, model_bytes):
        st = nsbmd.model_stats(self.built)
        return dict(polygons=st["polygons"], stock_polygons=self.stock_stats["polygons"],
                    vertices_sent=st["vertices_sent"], model_bytes=len(model_bytes),
                    stock_model_bytes=len(self.sec["model"]), materials=len(self.built["materials"]),
                    dropped_faces=self.dropped, clipped_faces=self.clipped,
                    untouched_stock_shapes=len(self.model["shapes"]) - len(self.faces))


def stock_shapes_identical(old_model, new_model, edited_names):
    """Every stock shape not in edited_names keeps its display list and its material record byte for byte."""
    om = {s["name"]: s for s in old_model["shapes"]}
    nm = {s["name"]: s for s in new_model["shapes"]}
    bad = [n for n, s in om.items() if n not in edited_names and (n not in nm or nm[n]["dl"] != s["dl"])]
    omat = {x["name"]: nsbmd.build_mat(x) for x in old_model["materials"]}
    nmat = {x["name"]: nsbmd.build_mat(x) for x in new_model["materials"]}
    bad += [n for n, b in omat.items() if nmat.get(n) != b]
    return bad


# ---------------------------------------------------------------------------------------------------------------
# camera polygon count (method of tools/lake_verity/assemble.camera_polys, CAMERA_TYPE_DEFAULT)
# ---------------------------------------------------------------------------------------------------------------

PITCH, DIST, HALF_FOV = 59.051513671875, 666.922119140625, 8.0914306640625
NEAR, FAR = 150.0, 900.0


def camera_faces(models):
    """models: [(model dict, (cx, cz))] -> list of (world vertices, double sided) for every face."""
    out = []
    for model, (cx, cz) in models:
        mesh = nsbmd.model_to_mesh(model, (cx, cz))
        cull = {mt["name"]: mt.get("polygon_attr", {}).get("cull", "back") for mt in mesh["materials"]}
        for me in mesh["meshes"]:
            P = [(p[0] * 16.0, 16.0 + p[1] * 16.0, p[2] * 16.0) for p in me["positions"]]
            ds = cull.get(me["material"], "back") != "back"
            for f in me["quads"] + me["tris"]:
                out.append(([P[i] for i in f], ds))
    return out


def camera_polys(faces, tiles):
    """Worst count of faces in the view (frustum + back-face culling) over the player tiles; returns (max, tile)."""
    p = math.radians(PITCH)
    tf = math.tan(math.radians(HALF_FOV))
    best = (0, None)
    for (tx, tz) in tiles:
        tgt = ((tx + 0.5) * 16.0, 32.0, (tz + 0.5) * 16.0)
        cam = (tgt[0], tgt[1] + DIST * math.sin(p), tgt[2] + DIST * math.cos(p))
        fwd = _norm(_sub(tgt, cam))
        right = _norm(_cross(fwd, (0.0, 1.0, 0.0)))
        up = _cross(right, fwd)
        n = 0
        for pts, ds in faces:
            c = [sum(q[k] for q in pts) / len(pts) for k in range(3)]
            inside = False
            for q in pts:
                d = _sub(q, cam)
                zc = sum(d[k] * fwd[k] for k in range(3))
                if zc < NEAR or zc > FAR:
                    continue
                xc = sum(d[k] * right[k] for k in range(3))
                yc = sum(d[k] * up[k] for k in range(3))
                if abs(xc) <= zc * tf * 4 / 3 and abs(yc) <= zc * tf:
                    inside = True
                    break
            if not inside:
                continue
            if not ds:
                nrm = _cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0]))
                if sum(nrm[k] * (cam[k] - c[k]) for k in range(3)) <= 0:
                    continue
            n += 1
        if n > best[0]:
            best = (n, (tx, tz))
    return best
