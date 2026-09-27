#!/usr/bin/env python3
"""NSBMD (BMD0 / MDL0 [+ TEX0]) reader and writer for field map chunk models. See docs/lake_verity_redesign/pipeline.md.

Standard library only. Implements the documented NNS G3D binary layout:

  BMD0 header: 'BMD0', u16 0xFEFF, u16 version 2, u32 file size, u16 16, u16 section count, u32 section offsets
  MDL0 block:  'MDL0', u32 size, dictionary of models (u32 offset from the MDL0 block)
  model:       u32 size, u32 ofsSbc, u32 ofsMat, u32 ofsShp, u32 ofsEvpMtx, NNSG3dResMdlInfo (0x2C bytes),
               node info (dictionary of u32 offsets + node data), SBC byte code, materials, shapes, envelopes
  materials:   u16 ofsDictTexToMatList, u16 ofsDictPlttToMatList, dictionary of u32 material offsets,
               texture->material and palette->material dictionaries ({u16 list offset, u8 count, u8 bound}),
               u8 material index lists, NNSG3dResMatData records
  shapes:      dictionary of u32 shape offsets, NNSG3dResShpData {u16 tag, u16 size, u32 flag, u32 ofsDL, u32 sizeDL},
               then the GX display lists

Usage:
  python3 tools/lake_verity/nsbmd.py info <file.nsbmd | map_data_NNN.bin>
  python3 tools/lake_verity/nsbmd.py dump <map_data_NNN.bin> <out.mesh.json>    (chunk-local + absolute tiles)

World units: a map chunk is 512 x 512 units (32 tiles of 16). A vertex is fx16 (1/4096) in the display list and
is multiplied by the model's posScale (SBC POSSCALE), so world = fx16 / 4096 * posScale. The chunk model is drawn
with its origin at the chunk centre (land_data.c LandDataManager_CalculateRenderingPosition).
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "coronet_lava"))

import nnsdict  # noqa: E402

FX = 4096.0
TILE = 16.0
GROUND_Y = 16.0   # world y of the lake shore ground (stock BDHC); layout.py / mesh.json h = (y - GROUND_Y) / TILE

# ---------------------------------------------------------------------------------------------------------------
# GX display lists
# ---------------------------------------------------------------------------------------------------------------

# command -> parameter word count
GX_PARAMS = {
    0x00: 0, 0x10: 1, 0x11: 0, 0x12: 1, 0x13: 1, 0x14: 1, 0x15: 0, 0x16: 16, 0x17: 12, 0x18: 16, 0x19: 12,
    0x1A: 9, 0x1B: 3, 0x1C: 3, 0x20: 1, 0x21: 1, 0x22: 1, 0x23: 2, 0x24: 1, 0x25: 1, 0x26: 1, 0x27: 1,
    0x28: 1, 0x29: 1, 0x2A: 1, 0x2B: 1, 0x30: 1, 0x31: 1, 0x32: 1, 0x33: 1, 0x34: 32, 0x40: 1, 0x41: 0,
    0x50: 1, 0x60: 1, 0x70: 3, 0x71: 2, 0x72: 1,
}
NOP, MTX_RESTORE, COLOR, NORMAL, TEXCOORD, VTX_16, VTX_10, VTX_XY, VTX_XZ, VTX_YZ, VTX_DIFF, BEGIN, END = (
    0x00, 0x14, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x40, 0x41)
PRIM_TRI, PRIM_QUAD, PRIM_TRISTRIP, PRIM_QUADSTRIP = 0, 1, 2, 3


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def dl_decode(dl):
    """Packed display list -> [(cmd, [params])]. Padding NOPs inside a packed word are kept as (0, [])."""
    out, o = [], 0
    while o + 4 <= len(dl):
        ops = dl[o:o + 4]
        o += 4
        for c in ops:
            n = GX_PARAMS[c]
            out.append((c, list(struct.unpack_from("<%dI" % n, dl, o))))
            o += 4 * n
    assert o == len(dl), (o, len(dl))
    return out


def dl_encode(cmds):
    """[(cmd, [params])] -> packed display list. Groups 4 commands per word, pads the last word with NOPs."""
    out = bytearray()
    for i in range(0, len(cmds), 4):
        grp = list(cmds[i:i + 4])
        while len(grp) < 4:
            grp.append((NOP, []))
        out += bytes(c for c, _ in grp)
        for _, p in grp:
            out += struct.pack("<%dI" % len(p), *p)
    return bytes(out)


def dl_primitives(cmds):
    """Runs the vertex commands of a display list. Returns [(prim_type, [vertex])] where a vertex is
    {"pos": (x, y, z) fx16 ints, "uv": (s, t) 1/16 texel ints or None, "color": rgb555 or None, "normal": raw or None}."""
    prims, cur = [], None
    pos = [0, 0, 0]
    uv = color = normal = None
    for c, p in cmds:
        if c == BEGIN:
            cur = (p[0] & 3, [])
            prims.append(cur)
        elif c == END:
            cur = None
        elif c == COLOR:
            color = p[0] & 0x7FFF
        elif c == NORMAL:
            normal = p[0] & 0x3FFFFFFF
        elif c == TEXCOORD:
            uv = (sx(p[0], 16), sx(p[0] >> 16, 16))
        elif c in (VTX_16, VTX_10, VTX_XY, VTX_XZ, VTX_YZ, VTX_DIFF):
            if c == VTX_16:
                pos = [sx(p[0], 16), sx(p[0] >> 16, 16), sx(p[1], 16)]
            elif c == VTX_10:
                pos = [sx(p[0], 10) << 6, sx(p[0] >> 10, 10) << 6, sx(p[0] >> 20, 10) << 6]
            elif c == VTX_XY:
                pos = [sx(p[0], 16), sx(p[0] >> 16, 16), pos[2]]
            elif c == VTX_XZ:
                pos = [sx(p[0], 16), pos[1], sx(p[0] >> 16, 16)]
            elif c == VTX_YZ:
                pos = [pos[0], sx(p[0], 16), sx(p[0] >> 16, 16)]
            else:
                pos = [sx(pos[0] + sx(p[0], 10), 16), sx(pos[1] + sx(p[0] >> 10, 10), 16),
                       sx(pos[2] + sx(p[0] >> 20, 10), 16)]
            assert cur is not None, "vertex outside BEGIN/END"
            cur[1].append({"pos": tuple(pos), "uv": uv, "color": color, "normal": normal})
    return prims


def prims_to_faces(prims):
    """Expands strips. Returns (tris, quads) as lists of vertex-dict tuples, preserving the GX winding
    (strip triangles alternate so every face keeps the same facing)."""
    tris, quads = [], []
    for t, vs in prims:
        if t == PRIM_TRI:
            tris += [tuple(vs[i:i + 3]) for i in range(0, len(vs) - 2, 3)]
        elif t == PRIM_QUAD:
            quads += [tuple(vs[i:i + 4]) for i in range(0, len(vs) - 3, 4)]
        elif t == PRIM_TRISTRIP:
            for i in range(len(vs) - 2):
                tris.append((vs[i], vs[i + 1], vs[i + 2]) if i % 2 == 0 else (vs[i + 1], vs[i], vs[i + 2]))
        else:
            for i in range(0, len(vs) - 3, 2):
                quads.append((vs[i], vs[i + 1], vs[i + 3], vs[i + 2]))
    return tris, quads


def rgb555(c):
    return ((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31)


def to_rgb555(c):
    return (round(c[0] * 31 / 255) & 31) | ((round(c[1] * 31 / 255) & 31) << 5) | ((round(c[2] * 31 / 255) & 31) << 10)


def normal_vec(n):
    return (sx(n, 10) / 512.0, sx(n >> 10, 10) / 512.0, sx(n >> 20, 10) / 512.0)


# ---------------------------------------------------------------------------------------------------------------
# display list encoder (geometry -> GX commands)
# ---------------------------------------------------------------------------------------------------------------

def vtx_cmd(pos, prev, allow_diff=False):
    """Vertex command for pos given the previous vertex (None at the start of a shape), chosen the way the stock
    map models are encoded: a 1-word VTX_XY / VTX_XZ / VTX_YZ when one coordinate repeats, else VTX_10 when all
    three are multiples of 64, else VTX_16. VTX_DIFF is never used by the stock models (allow_diff enables it)."""
    x, y, z = pos
    if prev is not None:
        if allow_diff:
            d = [pos[i] - prev[i] for i in range(3)]
            if all(-512 <= v <= 511 for v in d):
                return VTX_DIFF, [(d[0] & 0x3FF) | ((d[1] & 0x3FF) << 10) | ((d[2] & 0x3FF) << 20)]
        if z == prev[2]:
            return VTX_XY, [(x & 0xFFFF) | ((y & 0xFFFF) << 16)]
        if y == prev[1]:
            return VTX_XZ, [(x & 0xFFFF) | ((z & 0xFFFF) << 16)]
        if x == prev[0]:
            return VTX_YZ, [(y & 0xFFFF) | ((z & 0xFFFF) << 16)]
    if all(v & 63 == 0 for v in pos):
        return VTX_10, [((x >> 6) & 0x3FF) | (((y >> 6) & 0x3FF) << 10) | (((z >> 6) & 0x3FF) << 20)]
    return VTX_16, [(x & 0xFFFF) | ((y & 0xFFFF) << 16), z & 0xFFFF]


def encode_prims(prims, use_color=True, use_uv=True, use_normal=True):
    """[(prim_type, [vertex])] -> GX commands, per vertex TEXCOORD, COLOR, NORMAL (each only when it changed since
    the previous vertex of the shape), then the vertex. Matches the stock g3dcvtr output order."""
    cmds = []
    prev = None
    last = {"color": None, "uv": None, "normal": None}
    for t, vs in prims:
        cmds.append((BEGIN, [t]))
        for v in vs:
            if use_uv and v.get("uv") is not None and v["uv"] != last["uv"]:
                s, tt = v["uv"]
                cmds.append((TEXCOORD, [(s & 0xFFFF) | ((tt & 0xFFFF) << 16)]))
                last["uv"] = v["uv"]
            if use_color and v.get("color") is not None and v["color"] != last["color"]:
                cmds.append((COLOR, [v["color"]]))
                last["color"] = v["color"]
            if use_normal and v.get("normal") is not None and v["normal"] != last["normal"]:
                cmds.append((NORMAL, [v["normal"]]))
                last["normal"] = v["normal"]
            cmds.append(vtx_cmd(v["pos"], prev))
            prev = v["pos"]
        cmds.append((END, []))
    return cmds


def dl_pack(cmds):
    """Packs commands like g3dcvtr: 4 per word; an END in the last slot of a word is followed by a NOP word,
    and the list ends with its partial word padded plus one NOP word."""
    words = []
    cur = []
    for c in cmds:
        cur.append(c)
        if len(cur) == 4:
            words.append(cur)
            cur = []
            if c[0] == END:
                words.append([(NOP, [])] * 4)
    if cur:
        cur += [(NOP, [])] * (4 - len(cur))
        words.append(cur)
        words.append([(NOP, [])] * 4)
    return dl_encode([c for w in words for c in w])


def _vkey(v):
    return (tuple(v["pos"]), tuple(v["uv"]) if v.get("uv") is not None else None, v.get("color"), v.get("normal"))


def faces_to_prims(tris, quads):
    """Faces (tuples of vertex dicts, GX winding) -> primitive runs. Quads that share an edge in strip order are
    chained greedily into quad strips (a strip of n quads sends 2n+2 vertices instead of 4n); lone quads go into one
    quad list; triangles go into one triangle list."""
    prims = []
    remaining = list(range(len(quads)))
    by_start = {}
    for i, q in enumerate(quads):
        by_start.setdefault((_vkey(q[0]), _vkey(q[1])), []).append(i)
    used = [False] * len(quads)
    # a quad that some other quad continues into is not a strip start; start from quads nobody leads into first
    leads_in = set()
    for i, q in enumerate(quads):
        for j in by_start.get((_vkey(q[3]), _vkey(q[2])), []):
            if j != i:
                leads_in.add(j)
    order = [i for i in remaining if i not in leads_in] + [i for i in remaining if i in leads_in]
    singles = []
    for i in order:
        if used[i]:
            continue
        used[i] = True
        chain = [quads[i]]
        while True:
            q = chain[-1]
            nxt = next((j for j in by_start.get((_vkey(q[3]), _vkey(q[2])), []) if not used[j]), None)
            if nxt is None:
                break
            used[nxt] = True
            chain.append(quads[nxt])
        if len(chain) == 1:
            singles.append(chain[0])
        else:
            vs = [chain[0][0], chain[0][1]]
            for q in chain:
                vs += [q[3], q[2]]
            prims.append((PRIM_QUADSTRIP, vs))
    if singles:
        prims.append((PRIM_QUAD, [v for q in singles for v in q]))
    if tris:
        prims.append((PRIM_TRI, [v for t in tris for v in t]))
    return prims


# ---------------------------------------------------------------------------------------------------------------
# material data
# ---------------------------------------------------------------------------------------------------------------

MATFLAG = {"texmtx_use": 0x0001, "texmtx_scaleone": 0x0002, "texmtx_rotzero": 0x0004, "texmtx_transzero": 0x0008,
           "origwh_same": 0x0010, "wireframe": 0x0020, "diffuse": 0x0040, "ambient": 0x0080, "vtxcolor": 0x0100,
           "specular": 0x0200, "emission": 0x0400, "shininess": 0x0800, "texplttbase": 0x1000, "effectmtx": 0x2000}


def parse_mat(d, o):
    tag, size, diff_amb, spec_emi, poly_attr, poly_mask, tex_param, tex_mask, pltt_base, flag, ow, oh, magw, magh = \
        struct.unpack_from("<HHIIIIIIHHHHii", d, o)
    m = dict(tag=tag, size=size, diff_amb=diff_amb, spec_emi=spec_emi, poly_attr=poly_attr, poly_attr_mask=poly_mask,
             tex_image_param=tex_param, tex_image_param_mask=tex_mask, tex_pltt_base=pltt_base, flag=flag,
             orig_width=ow, orig_height=oh, mag_w=magw, mag_h=magh)
    p = o + 0x2C
    if not flag & MATFLAG["texmtx_scaleone"]:
        m["scale_s"], m["scale_t"] = struct.unpack_from("<ii", d, p)
        p += 8
    if not flag & MATFLAG["texmtx_rotzero"]:
        m["rot_sin"], m["rot_cos"] = struct.unpack_from("<hh", d, p)
        p += 4
    if not flag & MATFLAG["texmtx_transzero"]:
        m["trans_s"], m["trans_t"] = struct.unpack_from("<ii", d, p)
        p += 8
    if flag & MATFLAG["effectmtx"]:
        m["effect_mtx"] = list(struct.unpack_from("<16i", d, p))
        p += 64
    m["extra"] = d[p:o + size].hex()   # anything the layout above does not account for (expected empty)
    return m


def build_mat(m):
    body = struct.pack("<IIIIIIHHHHii", m["diff_amb"], m["spec_emi"], m["poly_attr"], m["poly_attr_mask"],
                       m["tex_image_param"], m["tex_image_param_mask"], m["tex_pltt_base"], m["flag"],
                       m["orig_width"], m["orig_height"], m["mag_w"], m["mag_h"])
    f = m["flag"]
    if not f & MATFLAG["texmtx_scaleone"]:
        body += struct.pack("<ii", m["scale_s"], m["scale_t"])
    if not f & MATFLAG["texmtx_rotzero"]:
        body += struct.pack("<hh", m["rot_sin"], m["rot_cos"])
    if not f & MATFLAG["texmtx_transzero"]:
        body += struct.pack("<ii", m["trans_s"], m["trans_t"])
    if f & MATFLAG["effectmtx"]:
        body += struct.pack("<16i", *m["effect_mtx"])
    body += bytes.fromhex(m.get("extra", ""))
    return struct.pack("<HH", m.get("tag", 0), 4 + len(body)) + body


def poly_attr_info(pa):
    # bits 6/7 are "render back face" / "render front face"; cull names the faces that are NOT drawn
    return dict(lights=pa & 15, mode=(pa >> 4) & 3, cull={0: "both", 1: "front", 2: "back", 3: "none"}[(pa >> 6) & 3],
                back_display=bool(pa & 0x40), front_display=bool(pa & 0x80), translucent_depth=bool(pa & 0x800),
                far_clip=bool(pa & 0x1000), dot_1px=bool(pa & 0x2000), depth_equal=bool(pa & 0x4000),
                fog=bool(pa & 0x8000), alpha=(pa >> 16) & 31, polygon_id=(pa >> 24) & 63)


def tex_param_info(tp):
    return dict(repeat_s=bool(tp & 1 << 16), repeat_t=bool(tp & 1 << 17), flip_s=bool(tp & 1 << 18),
                flip_t=bool(tp & 1 << 19), width=8 << ((tp >> 20) & 7), height=8 << ((tp >> 23) & 7),
                format=(tp >> 26) & 7, color0_transparent=bool(tp & 1 << 29), texgen=(tp >> 30) & 3)


# ---------------------------------------------------------------------------------------------------------------
# dictionary helpers
# ---------------------------------------------------------------------------------------------------------------

def dict_entries(d, o):
    """[(name bytes(16), entry bytes)] of the NNS dictionary at o; plus the dictionary byte size."""
    nodes, names, _ = nnsdict.parse(d, o)
    eb = o + struct.unpack_from("<H", d, o + 6)[0]
    unit = struct.unpack_from("<H", d, eb)[0]
    ents = [d[eb + 4 + unit * i:eb + 4 + unit * (i + 1)] for i in range(len(names))]
    size = struct.unpack_from("<H", d, o + 2)[0]
    return list(zip(names, ents)), size


def dict_build(names, entries):
    """nnsdict.build, with the patricia tree nodes renumbered in pre-order (left child first), which is the
    numbering g3dcvtr writes; the tree itself is identical, so this only matters for byte-identical output."""
    if not names:
        # empty dictionary (a root node only): 8-byte header + 1 node + 4-byte entry block header
        return struct.pack("<BBHHH", 0, 0, 16, 8, 12) + bytes([0x7F, 0, 0, 0]) + struct.pack("<HH", 4, 4)
    raw = nnsdict.build([n.rstrip(b"\0") if isinstance(n, bytes) else n.encode() for n in names], entries)
    n = raw[1]
    nodes = [list(raw[8 + 4 * i:12 + 4 * i]) for i in range(n + 1)]
    order = [0]

    def visit(i, parent_bit):
        if i == 0 or nodes[i][0] >= parent_bit:
            return
        order.append(i)
        visit(nodes[i][1], nodes[i][0])
        visit(nodes[i][2], nodes[i][0])

    visit(nodes[0][1], 0x80)
    remap = {old: new for new, old in enumerate(order)}
    out = [None] * len(nodes)
    for old, nd in enumerate(nodes):
        out[remap[old]] = [nd[0], remap[nd[1]], remap[nd[2]], nd[3]]
    return raw[:8] + b"".join(bytes(x) for x in out) + raw[8 + 4 * (n + 1):]


def nm(b):
    return b.rstrip(b"\0").decode("latin1")


# ---------------------------------------------------------------------------------------------------------------
# model reader
# ---------------------------------------------------------------------------------------------------------------

SBC_LEN = {0x00: 1, 0x01: 1, 0x02: 3, 0x03: 2, 0x04: 2, 0x05: 2, 0x06: 4, 0x07: 2, 0x08: 2, 0x0A: 9, 0x0B: 1,
           0x0C: 3, 0x0D: 3}


def sbc_decode(b):
    out, o = [], 0
    while o < len(b):
        op = b[o]
        base = op & 0x1F
        n = SBC_LEN[base]
        if base in (0x06, 0x07, 0x08):
            n += {0x00: 0, 0x20: 1, 0x40: 1, 0x60: 2}[op & 0x60]
        elif base == 0x09:
            n = 3 + 3 * b[o + 2]
        out.append(bytes(b[o:o + n]))
        o += n
        if base == 0x01:
            break
    return out, bytes(b[o:])


def read_container(data):
    """Returns (data, {stamp: offset})."""
    assert data[:4] == b"BMD0", data[:4]
    n = struct.unpack_from("<H", data, 14)[0]
    offs = struct.unpack_from("<%dI" % n, data, 16)
    return {data[o:o + 4].decode(): o for o in offs}


def parse_model(data, mo):
    size, ofs_sbc, ofs_mat, ofs_shp, ofs_evp = struct.unpack_from("<5I", data, mo)
    info_raw = struct.unpack_from("<8BiiHHHH6hii", data, mo + 0x14)
    keys = ["sbc_type", "scaling_rule", "tex_mtx_mode", "num_node", "num_mat", "num_shp", "first_unused_mtx_stack_id",
            "dummy", "pos_scale", "inv_pos_scale", "num_vertex", "num_polygon", "num_triangle", "num_quad",
            "box_x", "box_y", "box_z", "box_w", "box_h", "box_d", "box_pos_scale", "box_inv_pos_scale"]
    info = dict(zip(keys, info_raw))
    # nodes
    no = mo + 0x40
    nents, _ = dict_entries(data, no)
    offs = [struct.unpack("<I", e)[0] for _, e in nents]
    node_end = mo + ofs_sbc
    nodes = []
    for i, (name, e) in enumerate(nents):
        a = no + offs[i]
        b = no + offs[i + 1] if i + 1 < len(offs) else node_end
        nodes.append({"name": nm(name), "data": data[a:b].hex()})
    # SBC
    sbc_cmds, sbc_pad = sbc_decode(data[mo + ofs_sbc:mo + ofs_mat])
    # materials
    mat_o = mo + ofs_mat
    ofs_tex, ofs_pl = struct.unpack_from("<HH", data, mat_o)
    ments, _ = dict_entries(data, mat_o + 4)
    mat_offs = [struct.unpack("<I", e)[0] for _, e in ments]
    tents, _ = dict_entries(data, mat_o + ofs_tex)
    pents, _ = dict_entries(data, mat_o + ofs_pl)

    def binds(ents):
        out = []
        for name, e in ents:
            lo, cnt, flag = struct.unpack("<HBB", e)
            out.append({"name": nm(name), "mats": list(data[mat_o + lo:mat_o + lo + cnt]), "flag": flag,
                        "list_offset": lo})
        return out

    tex_bind, pl_bind = binds(tents), binds(pents)
    mats = []
    for i, (name, _) in enumerate(ments):
        m = parse_mat(data, mat_o + mat_offs[i])
        m["name"] = nm(name)
        m["texture"] = next((b["name"] for b in tex_bind if i in b["mats"]), None)
        m["palette"] = next((b["name"] for b in pl_bind if i in b["mats"]), None)
        mats.append(m)
    # shapes
    shp_o = mo + ofs_shp
    sents, _ = dict_entries(data, shp_o)
    shapes = []
    for name, e in sents:
        so = shp_o + struct.unpack("<I", e)[0]
        tag, ssize, flag, ofs_dl, size_dl = struct.unpack_from("<HHIII", data, so)
        dl = data[so + ofs_dl:so + ofs_dl + size_dl]
        shapes.append({"name": nm(name), "tag": tag, "size": ssize, "flag": flag, "dl": dl,
                       "hdr_extra": data[so + 16:so + ssize].hex()})
    evp = data[mo + ofs_evp:mo + size]
    return {"name": None, "info": info, "nodes": nodes, "sbc": [c.hex() for c in sbc_cmds], "sbc_pad": sbc_pad.hex(),
            "materials": mats, "tex_bind": tex_bind, "pltt_bind": pl_bind, "shapes": shapes, "evp": evp.hex(),
            "layout": {"ofs_sbc": ofs_sbc, "ofs_mat": ofs_mat, "ofs_shp": ofs_shp, "ofs_evp": ofs_evp, "size": size,
                       "ofs_tex": ofs_tex, "ofs_pl": ofs_pl, "mat_offs": mat_offs}}


def parse_bmd(data):
    """Returns {"models": [model], "tex0": bytes or None, "version": int}."""
    secs = read_container(data)
    o = secs["MDL0"]
    ents, _ = dict_entries(data, o + 8)
    models = []
    for name, e in ents:
        m = parse_model(data, o + struct.unpack("<I", e)[0])
        m["name"] = nm(name)
        models.append(m)
    tex0 = None
    if "TEX0" in secs:
        t = secs["TEX0"]
        tex0 = data[t:t + struct.unpack_from("<I", data, t + 4)[0]]
    return {"models": models, "tex0": tex0, "version": struct.unpack_from("<H", data, 6)[0]}


def map_model_bytes(path):
    d = open(path, "rb").read()
    if d[:4] == b"BMD0":
        return d
    s = struct.unpack_from("<4I", d)
    o = 16 + s[0] + s[1]
    return d[o:o + s[2]]


# ---------------------------------------------------------------------------------------------------------------
# model writer
# ---------------------------------------------------------------------------------------------------------------

def align(b, n=4, pad=b"\0"):
    return b + pad * (-len(b) % n)


def build_model(m):
    """Serialises one model dict (as returned by parse_model, or built by make_model) to NNSG3dResMdl bytes."""
    info = m["info"]
    # node info
    node_datas = [bytes.fromhex(n["data"]) for n in m["nodes"]]
    probe = dict_build([n["name"] for n in m["nodes"]], [b"\0" * 4] * len(m["nodes"]))
    o = len(probe)
    offs = []
    for nd in node_datas:
        offs.append(o)
        o += len(nd)
    node_blk = dict_build([n["name"] for n in m["nodes"]], [struct.pack("<I", x) for x in offs]) + b"".join(node_datas)
    # sbc
    sbc = b"".join(bytes.fromhex(c) for c in m["sbc"])
    sbc = sbc + bytes.fromhex(m["sbc_pad"]) if m.get("sbc_pad") is not None else align(sbc)
    # materials
    mats = m["materials"]
    mat_names = [x["name"] for x in mats]
    tex_bind, pl_bind = m["tex_bind"], m["pltt_bind"]
    mdict_probe = dict_build(mat_names, [b"\0" * 4] * len(mats))
    tdict_probe = dict_build([b["name"] for b in tex_bind], [b"\0" * 4] * len(tex_bind))
    pdict_probe = dict_build([b["name"] for b in pl_bind], [b"\0" * 4] * len(pl_bind))
    ofs_tex = 4 + len(mdict_probe)
    ofs_pl = ofs_tex + len(tdict_probe)
    o = ofs_pl + len(pdict_probe)
    lists = b""
    tents, pents = [], []
    for binds, ents in ((tex_bind, tents), (pl_bind, pents)):
        for b in binds:
            ents.append(struct.pack("<HBB", o + len(lists), len(b["mats"]), b.get("flag", 0)))
            lists += bytes(b["mats"])
    lists = align(lists)
    o += len(lists)
    mat_blobs, mat_offs = [], []
    for x in mats:
        mat_offs.append(o)
        blob = build_mat(x)
        mat_blobs.append(blob)
        o += len(blob)
    mat_blk = struct.pack("<HH", ofs_tex, ofs_pl) + dict_build(mat_names, [struct.pack("<I", v) for v in mat_offs])
    mat_blk += dict_build([b["name"] for b in tex_bind], tents) + dict_build([b["name"] for b in pl_bind], pents)
    mat_blk += lists + b"".join(mat_blobs)
    # shapes: headers first, then display lists (as g3dcvtr lays them out)
    shps = m["shapes"]
    sdict_probe = dict_build([s["name"] for s in shps], [b"\0" * 4] * len(shps))
    hdr_sizes = [16 + len(bytes.fromhex(s.get("hdr_extra", ""))) for s in shps]
    o = len(sdict_probe)
    hdr_offs = []
    for hs in hdr_sizes:
        hdr_offs.append(o)
        o += hs
    dl_offs = []
    for s in shps:
        dl_offs.append(o)
        o += len(s["dl"])
    hdrs = b""
    for i, s in enumerate(shps):
        hdrs += struct.pack("<HHIII", s.get("tag", 0), hdr_sizes[i], s["flag"], dl_offs[i] - hdr_offs[i], len(s["dl"]))
        hdrs += bytes.fromhex(s.get("hdr_extra", ""))
    shp_blk = dict_build([s["name"] for s in shps], [struct.pack("<I", v) for v in hdr_offs]) + hdrs
    shp_blk += b"".join(s["dl"] for s in shps)
    evp = bytes.fromhex(m.get("evp", ""))
    # assemble
    ofs_sbc = 0x40 + len(node_blk)
    ofs_mat = ofs_sbc + len(sbc)
    ofs_shp = ofs_mat + len(mat_blk)
    ofs_evp = ofs_shp + len(shp_blk)
    size = ofs_evp + len(evp)
    keys = ["sbc_type", "scaling_rule", "tex_mtx_mode", "num_node", "num_mat", "num_shp", "first_unused_mtx_stack_id",
            "dummy", "pos_scale", "inv_pos_scale", "num_vertex", "num_polygon", "num_triangle", "num_quad",
            "box_x", "box_y", "box_z", "box_w", "box_h", "box_d", "box_pos_scale", "box_inv_pos_scale"]
    hdr = struct.pack("<5I", size, ofs_sbc, ofs_mat, ofs_shp, ofs_evp)
    hdr += struct.pack("<8BiiHHHH6hii", *[info[k] for k in keys])
    return hdr + node_blk + sbc + mat_blk + shp_blk + evp


def build_bmd(models, tex0=None, version=2):
    """models: [model dict]. Returns BMD0 bytes with an MDL0 block (and an optional raw TEX0 block)."""
    blobs = [build_model(m) for m in models]
    probe = dict_build([m["name"] for m in models], [b"\0" * 4] * len(models))
    o = 8 + len(probe)
    offs = []
    for b in blobs:
        offs.append(o)
        o += len(b)
    body = dict_build([m["name"] for m in models], [struct.pack("<I", v) for v in offs]) + b"".join(blobs)
    mdl0 = b"MDL0" + struct.pack("<I", 8 + len(body)) + body
    nsec = 2 if tex0 else 1
    hdr_size = 16
    sec_offs = [hdr_size + 4 * nsec]
    if tex0:
        sec_offs.append(sec_offs[0] + len(mdl0))
    total = sec_offs[0] + len(mdl0) + (len(tex0) if tex0 else 0)
    out = b"BMD0" + struct.pack("<HHIHH", 0xFEFF, version, total, hdr_size, nsec) + struct.pack("<%dI" % nsec, *sec_offs)
    return out + mdl0 + (tex0 or b"")


# ---------------------------------------------------------------------------------------------------------------
# model from scratch (stock map-model conventions)
# ---------------------------------------------------------------------------------------------------------------

def make_poly_attr(lights=1, cull="back", alpha=31, polygon_id=0, fog=True, translucent_depth=False, mode=0):
    """cull: faces that are not drawn ("back" = stock, "none" = double sided)."""
    show = {"back": 0x80, "front": 0x40, "none": 0xC0, "both": 0}[cull]
    return (lights & 15) | (mode & 3) << 4 | show | (0x800 if translucent_depth else 0) | (0x8000 if fog else 0) | \
        (alpha & 31) << 16 | (polygon_id & 63) << 24


def make_material(name, texture, palette, width, height, repeat=(True, True), flip=(False, False), **attr):
    """A material laid out like the stock map materials (flag 0x1fce, lit by light 0, diffuse 25/25/25 with the
    vertex-colour bit, white ambient, no texture matrix). The TEX_IMAGE_PARAM keeps only repeat/flip bits; the
    size/format/address come from the texture set at bind time. width/height are the texture size in texels."""
    tp = (1 << 16 if repeat[0] else 0) | (1 << 17 if repeat[1] else 0) | (1 << 18 if flip[0] else 0) | \
        (1 << 19 if flip[1] else 0)
    return dict(name=name, texture=texture, palette=palette, tag=0, diff_amb=0x7FFFE739, spec_emi=0,
                poly_attr=make_poly_attr(**attr), poly_attr_mask=0x3F1FF8FF, tex_image_param=tp,
                tex_image_param_mask=0xFFFFFFFF, tex_pltt_base=0, flag=0x1FCE, orig_width=width, orig_height=height,
                mag_w=4096, mag_h=4096, extra="")


def make_model(name, materials, shapes, draw=None, pos_scale=0x40000, node_name="polySurface1"):
    """Builds a model dict (for build_model / build_bmd) from scratch.

    materials: [make_material(...)]; shapes: [(shape name, [(prim_type, [vertex])])], vertices as in dl_primitives
    (pos in fx16 before posScale, uv in 1/16 texels, color rgb555 or None, normal packed or None);
    draw: [(material index, shape index)] in draw order (default: shape i with material i).
    Header counts and the bounding box are computed from the geometry. Rebuilding the stock chunk models through
    this path is byte-identical except box_h/box_d, which g3dcvtr rounds from the unquantised source (1 unit, 1/32
    world unit, smaller); the box here rounds outward."""
    draw = draw if draw is not None else [(i, i) for i in range(len(shapes))]
    shp, nv, ntri, nquad, allpos = [], 0, 0, 0, []
    for sname, prims in shapes:
        cmds = encode_prims(prims)
        used = {c for c, _ in cmds}
        flag = (1 if NORMAL in used else 0) | (2 if COLOR in used else 0) | (4 if TEXCOORD in used else 0)
        shp.append({"name": sname, "tag": 0, "flag": flag, "dl": dl_pack(cmds), "hdr_extra": ""})
        for t, vs in prims:
            nv += len(vs)
            allpos += [v["pos"] for v in vs]
            if t == PRIM_TRI:
                ntri += len(vs) // 3
            elif t == PRIM_QUAD:
                nquad += len(vs) // 4
            elif t == PRIM_TRISTRIP:
                ntri += max(0, len(vs) - 2)
            else:
                nquad += max(0, (len(vs) - 2) // 2)
    box_ps = 0x80000
    k = box_ps // pos_scale   # box units per fx16 vertex unit ratio (2 for the stock 64/128 pair)
    mn = [min(p[i] for p in allpos) for i in range(3)] if allpos else [0, 0, 0]
    mx = [max(p[i] for p in allpos) for i in range(3)] if allpos else [0, 0, 0]
    box = [mn[i] // k for i in range(3)] + [-(-(mx[i] - mn[i]) // k) for i in range(3)]
    info = dict(sbc_type=0, scaling_rule=0, tex_mtx_mode=0, num_node=1, num_mat=len(materials), num_shp=len(shp),
                first_unused_mtx_stack_id=1, dummy=0, pos_scale=pos_scale, inv_pos_scale=(1 << 24) // pos_scale,
                num_vertex=nv, num_polygon=ntri + nquad, num_triangle=ntri, num_quad=nquad,
                box_x=box[0], box_y=box[1], box_z=box[2], box_w=box[3], box_h=box[4], box_d=box[5],
                box_pos_scale=box_ps, box_inv_pos_scale=(1 << 24) // box_ps)
    sbc = ["2600000000", "020001", "0b"] + ["04%02x" % mi + " 05%02x" % si for mi, si in draw] + ["2b", "01"]
    sbc = [x for c in sbc for x in c.split()]

    def binds(key):
        out = {}
        for i, m in enumerate(materials):
            if m.get(key):
                out.setdefault(m[key], []).append(i)
        return [{"name": n, "mats": out[n], "flag": 0} for n in sorted(out)]   # g3dcvtr sorts binds by name

    return {"name": name, "info": info, "nodes": [{"name": node_name, "data": "07f80010"}], "sbc": sbc,
            "sbc_pad": None, "materials": materials, "tex_bind": binds("texture"), "pltt_bind": binds("palette"),
            "shapes": shp, "evp": ""}


def model_prims(model):
    """[(shape name, prims)] of a parsed model, for feeding back into make_model."""
    return [(s["name"], dl_primitives(dl_decode(s["dl"]))) for s in model["shapes"]]


# ---------------------------------------------------------------------------------------------------------------
# geometry views
# ---------------------------------------------------------------------------------------------------------------

def shape_material_pairs(model):
    """[(material index, shape index)] in SBC draw order."""
    out, mat = [], None
    for c in model["sbc"]:
        b = bytes.fromhex(c)
        if b[0] & 0x1F == 0x04:
            mat = b[1]
        elif b[0] & 0x1F == 0x05:
            out.append((mat, b[1]))
    return out


def model_stats(model):
    nv = npoly = ntri = nquad = 0
    cmd_hist = {}
    for s in model["shapes"]:
        cmds = dl_decode(s["dl"])
        for c, _ in cmds:
            cmd_hist[c] = cmd_hist.get(c, 0) + 1
        for t, vs in dl_primitives(cmds):
            nv += len(vs)
            if t == PRIM_TRI:
                ntri += len(vs) // 3
            elif t == PRIM_QUAD:
                nquad += len(vs) // 4
            elif t == PRIM_TRISTRIP:
                ntri += max(0, len(vs) - 2)
            else:
                nquad += max(0, (len(vs) - 2) // 2)
    npoly = ntri + nquad
    return {"vertices_sent": nv, "polygons": npoly, "triangles": ntri, "quads": nquad, "gx_cmd_hist": cmd_hist}


def model_to_mesh(model, chunk_xy=(0, 0), name=None, offset=(0, 0, 0)):
    """Mesh dict in the PLAN.md format. Positions are given in tiles, both chunk-local (origin at the chunk's NW
    corner, "positions_local") and absolute matrix tiles ("positions"); h is layout.py h, (world y - 16) / 16. offset is a world-unit
    translation from the chunk centre (a map prop's position). UVs are texel / texture size with v in image space
    (0 = top row, as the DS samples); Blender and other GL-style importers use 1 - v."""
    ps = model["info"]["pos_scale"] / FX
    cx, cz = chunk_xy
    mats = model["materials"]
    out = {"name": name or model["name"], "origin_tile": [cx * 32, cz * 32], "pos_scale": model["info"]["pos_scale"],
           "materials": [], "meshes": []}
    for m in mats:
        tp = tex_param_info(m["tex_image_param"])
        pa = poly_attr_info(m["poly_attr"])
        out["materials"].append({"name": m["name"], "texture": m["texture"], "palette": m["palette"], "alpha": pa["alpha"],
                                 "size": [m["orig_width"], m["orig_height"]],
                                 "polygon_attr": pa, "tex_param": tp, "diff_amb": m["diff_amb"], "spec_emi": m["spec_emi"],
                                 "flag": m["flag"], "tex_mtx": {k: m[k] for k in ("scale_s", "scale_t", "rot_sin", "rot_cos",
                                                                                   "trans_s", "trans_t") if k in m}})
    for mi, si in shape_material_pairs(model):
        m = mats[mi]
        # map materials leave the size bits of TEX_IMAGE_PARAM at 0 (filled in when the texture is bound), so the
        # texture size comes from orig_width/orig_height
        w, h = m["orig_width"] or 8, m["orig_height"] or 8
        ss = m.get("scale_s", 4096) / FX
        st = m.get("scale_t", 4096) / FX
        cmds = dl_decode(model["shapes"][si]["dl"])
        tris, quads = prims_to_faces(dl_primitives(cmds))
        verts, index = [], {}

        def vid(v):
            k = (v["pos"], v["uv"], v["color"], v["normal"])
            if k not in index:
                index[k] = len(verts)
                verts.append(v)
            return index[k]

        mt = [[vid(v) for v in f] for f in tris]
        mq = [[vid(v) for v in f] for f in quads]
        ox, oy, oz = offset
        loc = [[(v["pos"][0] / FX * ps + ox) / TILE + 16, (v["pos"][1] / FX * ps + oy - GROUND_Y) / TILE,
                (v["pos"][2] / FX * ps + oz) / TILE + 16] for v in verts]
        out["meshes"].append({
            "material": m["name"], "shape": model["shapes"][si]["name"],
            "positions_local": loc,
            "positions": [[p[0] + cx * 32, p[1], p[2] + cz * 32] for p in loc],
            "uvs": [[(v["uv"][0] / 16.0) * ss / w, (v["uv"][1] / 16.0) * st / h] if v["uv"] else [0, 0] for v in verts],
            "colors": [list(rgb555(v["color"])) if v["color"] is not None else [255, 255, 255] for v in verts],
            "normals": [list(normal_vec(v["normal"])) if v["normal"] is not None else None for v in verts]
            if any(v["normal"] is not None for v in verts) else None,
            "tris": mt, "quads": mq})
    return out


def info_text(model):
    i = model["info"]
    st = model_stats(model)
    lines = [f"model {model['name']}: nodes={i['num_node']} mats={i['num_mat']} shps={i['num_shp']} "
             f"posScale={i['pos_scale'] / FX} header verts={i['num_vertex']} polys={i['num_polygon']} "
             f"tris={i['num_triangle']} quads={i['num_quad']}",
             f"  decoded: {st['vertices_sent']} vertices, {st['polygons']} polygons ({st['triangles']} tri, {st['quads']} quad)",
             "  gx cmds: " + " ".join(f"{c:02x}:{n}" for c, n in sorted(st["gx_cmd_hist"].items())),
             "  sbc: " + " ".join(model["sbc"])]
    for n in model["nodes"]:
        lines.append(f"  node {n['name']}: {n['data']}")
    for k, m in enumerate(model["materials"]):
        tp = tex_param_info(m["tex_image_param"])
        pa = poly_attr_info(m["poly_attr"])
        tm = {k2: m[k2] for k2 in ("scale_s", "scale_t", "rot_sin", "rot_cos", "trans_s", "trans_t") if k2 in m}
        lines.append(f"  mat {k:2d} {m['name']:16s} tex={m['texture']} pal={m['palette']} {m['orig_width']}x{m['orig_height']} "
                     f"fmt={tp['format']} rep={int(tp['repeat_s'])}{int(tp['repeat_t'])} flip={int(tp['flip_s'])}{int(tp['flip_t'])} "
                     f"texgen={tp['texgen']} alpha={pa['alpha']} cull={pa['cull']} lights={pa['lights']} id={pa['polygon_id']} "
                     f"fog={int(pa['fog'])} flag=0x{m['flag']:04x} da=0x{m['diff_amb']:08x} se=0x{m['spec_emi']:08x} {tm}")
    for k, s in enumerate(model["shapes"]):
        lines.append(f"  shp {k:2d} {s['name']:16s} flag=0x{s['flag']:x} dl={len(s['dl'])} bytes")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, path = sys.argv[1], sys.argv[2]
    bmd = parse_bmd(map_model_bytes(path))
    if cmd == "info":
        for m in bmd["models"]:
            print(info_text(m))
    elif cmd == "dump":
        base = os.path.basename(path)
        cid = int(base[9:12]) if base.startswith("map_data_") else None
        from layout import CHUNKS  # noqa: E402
        mesh = model_to_mesh(bmd["models"][0], CHUNKS.get(cid, (0, 0)), name=f"chunk_{cid}" if cid else None)
        with open(sys.argv[3], "w") as f:
            json.dump(mesh, f)
        print(f"wrote {sys.argv[3]}")


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main()
