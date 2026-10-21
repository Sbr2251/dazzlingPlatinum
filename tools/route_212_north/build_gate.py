#!/usr/bin/env python3
"""Builds the Route 212 North brass gate into overworld chunk map_data_085 (standard library only).

Usage:
  python3 tools/route_212_north/build_gate.py                 dry run: budgets + gameplay checks
  python3 tools/route_212_north/build_gate.py --write         write res/field/maps/data/map_data_085.bin
  python3 tools/route_212_north/build_gate.py --mesh OUT.json also dump the new geometry (mesh.json format)

Inputs: the stock chunk 085 at textures.BASE_REV (read from git, so re-running never feeds back) and the materials of
textures.py (run `textures.py --write` first so set 012 has them).

The top-left corner of Route 212 North (x 448..455, z 738..741) is forest in stock. It becomes a rock outcrop whose
south face leans back 20 degrees, with an ancient brass gate set into it (see README.md):

  - rock face (stock criffp/criffp2 cliff art, stock palettes) with an arched opening, x 448..456, 6 tiles up the slope;
  - a riveted brass arch ring and jambs (hanger texels, r212_brass palette);
  - brass bars behind the ring: the stock gold finials of the Pokemon Mansion fence (area07_hei_h), their tops
    following the arch, with two brass rails (blueglay texels, r212_plate);
  - a dark hall behind the bars (shadowchip, r212_dark), aged-rock returns (criffp, r212_aged), a stone floor;
  - a clock face over the arch and five gears on the rock (new r212_clock / r212_gear decals), stretched up the slope so
    the fixed field camera sees them round;
  - the east side of the outcrop (seen from the road); the facade top is a ridge with the stock tree row behind it.

Stock faces: the 6 trees inside the outcrop and two in front of it are dropped; tree-shadow and grass ground is cut
away under the outcrop and in a 4x2 clearing in front of the gate (x 450..453, z 742..743), which gets a stone apron
(z 742) and a row of stock tall grass (z 743, behaviour 0x02, so the Route 212 North land table, Klink included, rolls
right beside the gate). Every other stock shape keeps its display list and material byte for byte (checked).
Permissions: the clearing becomes walkable (it joins the stock grass strip at x 454..455); the outcrop stays blocked.
BDHC and props are stock (the whole corner is flat ground at world y 32).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import textures  # noqa: E402

BASE_REV = textures.BASE_REV
CHUNK_REL = "res/field/maps/data/map_data_085.bin"
CHUNK = (14, 23)                 # matrix cell: x 448..479, z 736..767
G = 1.0                          # ground h (world y 32)

# the outcrop and the clearing (tile-edge rectangles [x0, x1) x [z0, z1))
OUTCROP = (448, 738, 456, 742)
CLEARING = (450, 742, 454, 744)
# facade: bottom edge on z = ZF at ground level, leaning back by LEAN; (u, v) = (x, distance up the slope)
ZF = 742.0
LEAN = math.radians(20.0)
VF = 6.0                         # facade height up the slope
VBAND = 4.0                      # criffp below, criffp2 (grass fringe on top) above
X0, X1 = 448.0, 456.0
# arch
XC = 452.0
R = 1.5                          # opening half width = arch radius
T = 0.32                         # brass ring width
YS = 2.0                         # jamb height (slope units) where the arch starts
RO = R + T
NSEG = 10
BACK_SLOPE = math.radians(63.0)  # steeper than the camera pitch: always back-face culled
ZB = 740.35                      # the back wall of the hall (vertical), behind the facade at the arch top
# the fixed field camera (CAMERA_TYPE_DEFAULT) looks down at 59.05 deg: a length up the slope shows at
# cos(59.05 - 20) of its size, so round decals are stretched up the slope by the inverse
CAM_PITCH = math.radians(59.051513671875)
ROUND = 1.0 / math.cos(CAM_PITCH - LEAN)

TALL_GRASS = 0x0002              # tile behaviour of the stock tall grass on Route 212 North (chunk 087)
TREE_TEX = ("tree2_01", "conttree2_b", "conttree2_t")
GROUND_TEX = ("tshadow", "ngrass", "nhana")


def fp(u, v, d=0.0):
    """Facade point: u = x, v = slope distance from the ground line, d = offset along the facade normal (+ = out)."""
    sn, cs = math.sin(LEAN), math.cos(LEAN)
    return (u, G + v * cs + d * sn, ZF - v * sn + d * cs)


def area2(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) / 2


def facade_face(mb, mat, uv_pts, tex_uvs, d=0.0):
    """A face on the facade given in (u, v); wound counter-clockwise as seen from the front (u right, v up)."""
    if area2(uv_pts) < 0:
        uv_pts, tex_uvs = uv_pts[::-1], tex_uvs[::-1]
    mb.face(mat, [fp(u, v, d) for u, v in uv_pts], tex_uvs)


def rock_uv(u, v):
    return ((u - X0) / 2.0, (VF - v) / 2.0)


def rock_poly(mb, pts):
    """Rock polygon on the facade (convex, (u, v)); split at VBAND into criffp (below) and criffp2 (above)."""
    for lo, hi, mat in ((-1, VBAND, "r212_rock"), (VBAND, 99, "r212_rocktop")):
        poly = clip_band(pts, lo, hi)
        if len(poly) < 3:
            continue
        uvs = [rock_uv(u, v) for u, v in poly]
        if len(poly) <= 4:
            facade_face(mb, mat, poly, uvs)
        else:
            for k in range(1, len(poly) - 1):
                facade_face(mb, mat, [poly[0], poly[k], poly[k + 1]], [uvs[0], uvs[k], uvs[k + 1]])


def clip_band(pts, lo, hi):
    def clip(poly, keep, edge):
        out = []
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            ina, inb = keep(a), keep(b)
            if ina:
                out.append(a)
            if ina != inb:
                t = (edge - a[1]) / (b[1] - a[1])
                out.append((a[0] + (b[0] - a[0]) * t, edge))
        return out
    p = clip(pts, lambda q: q[1] >= lo, lo)
    if len(p) >= 3:
        p = clip(p, lambda q: q[1] <= hi, hi)
    return p


def decal(mb, mat, cu, cv, diameter, d):
    """A round decal on the facade, stretched up the slope so the camera sees it round."""
    hu, hv = diameter / 2, diameter / 2 * ROUND
    facade_face(mb, mat, [(cu - hu, cv - hv), (cu + hu, cv - hv), (cu + hu, cv + hv), (cu - hu, cv + hv)],
                [(0, 1), (1, 1), (1, 0), (0, 0)], d)


def build_gate(mb, stock):
    """All new geometry. stock: {texture: stock material dict} for reusing stock materials' textures/palettes."""
    for name, (tex, pal, size) in textures.MATERIALS.items():
        mb.material(name, tex, pal, size)
    mb.material("r212_rock", "criffp", "criff", (32, 32))
    mb.material("r212_rocktop", "criffp2", "criff2", (32, 32))
    mb.material("r212_tallgr", "nectgr", "nectgrass", (16, 16))
    mb.material("r212_stone", "blueglay", "blueglay", (16, 16))
    mb.material("r212_bar", "area07_hei_h", "area07_hei_h_pl", (16, 32))
    mb.material("r212_bar2", "area07_hei_h3", "area07_hei_h3_pl", (16, 32))
    mb.material("r212_tree", "tree2_01", "tree2_01", (64, 64))

    # --- rock face around the opening -------------------------------------------------------------------------
    rock_poly(mb, [(X0, 0), (XC - RO, 0), (XC - RO, VF), (X0, VF)])
    rock_poly(mb, [(XC + RO, 0), (X1, 0), (X1, VF), (XC + RO, VF)])
    rock_poly(mb, [(XC - RO, YS + RO), (XC + RO, YS + RO), (XC + RO, VF), (XC - RO, VF)])
    ang = [math.pi - k * math.pi / NSEG for k in range(NSEG + 1)]
    outer = [(XC + RO * math.cos(a), YS + RO * math.sin(a)) for a in ang]
    inner = [(XC + R * math.cos(a), YS + R * math.sin(a)) for a in ang]
    cl, cr = (XC - RO, YS + RO), (XC + RO, YS + RO)
    for k in range(NSEG):
        corner = cl if k < NSEG // 2 else cr
        rock_poly(mb, [outer[k], outer[k + 1], corner])

    # --- brass ring and jambs (one column of bosses across the band) --------------------------------------------
    per = 0.5 / T                 # texture units per tile along the band, so the bosses stay round
    s = 0.0
    for k in range(NSEG):
        seg = math.hypot(outer[k + 1][0] - outer[k][0], outer[k + 1][1] - outer[k][1])
        facade_face(mb, "r212_brass", [inner[k], inner[k + 1], outer[k + 1], outer[k]],
                    [(0.5, s * per), (0.5, (s + seg) * per), (0.0, (s + seg) * per), (0.0, s * per)])
        s += seg
    for x0, x1 in ((XC - RO, XC - R), (XC + R, XC + RO)):
        facade_face(mb, "r212_brass", [(x0, 0), (x1, 0), (x1, YS), (x0, YS)],
                    [(0, YS * per), (0.5, YS * per), (0.5, 0), (0, 0)])

    # --- the hall behind: floor, returns, back wall ------------------------------------------------------------
    sn, cs = math.sin(LEAN), math.cos(LEAN)
    top_y = (YS + R) * cs                                   # vertical height of the arch top
    mb.flat("r212_stone", XC - R, ZB, XC + R, ZF, G)
    back_h = top_y + 0.4
    mb.face("r212_dark", [(XC - R - 0.3, G, ZB), (XC + R + 0.3, G, ZB), (XC + R + 0.3, G + back_h, ZB),
                          (XC - R - 0.3, G + back_h, ZB)],
            [(0, back_h), (2 * R + 0.6, back_h), (2 * R + 0.6, 0), (0, 0)])
    for x, sign in ((XC - R, 1), (XC + R, -1)):             # left return faces east, right faces west
        zf_top = ZF - top_y * sn / cs
        pts = [(x, G, ZF), (x, G, ZB), (x, G + top_y, ZB), (x, G + top_y, zf_top)]
        uvs = [((ZF - p[2]) / 2, (G + top_y - p[1]) / 2) for p in pts]
        if sign < 0:
            pts, uvs = pts[::-1], uvs[::-1]
        mb.face("r212_aged", pts, uvs)

    # --- bars (stock gold finials) and rails -------------------------------------------------------------------
    nb = 6
    for i in range(nb):
        u = XC - R + R / nb + i * (2 * R / nb)
        vt = YS + math.sqrt(max(0.0, R * R - (u - XC) ** 2)) - 0.1
        mat = "r212_bar" if i in (2, 3) else "r212_bar2"
        # finial: the top tile of the texture (rows 0..15) on the top 0.9 of the bar, then the post repeats below
        facade_face(mb, mat, [(u - 0.5, vt - 0.9), (u + 0.5, vt - 0.9), (u + 0.5, vt), (u - 0.5, vt)],
                    [(0, 0.5), (1, 0.5), (1, 0), (0, 0)], -0.18)
        facade_face(mb, mat, [(u - 0.5, 0), (u + 0.5, 0), (u + 0.5, vt - 0.9), (u - 0.5, vt - 0.9)],
                    [(0, 1.0), (1, 1.0), (1, 0.5), (0, 0.5)], -0.18)
    for v in (0.55, 1.5):
        facade_face(mb, "r212_plate", [(XC - R, v), (XC + R, v), (XC + R, v + 0.17), (XC - R, v + 0.17)],
                    [(0, 0.34), (2 * R * 2, 0.34), (2 * R * 2, 0), (0, 0)], -0.12)

    # --- clock over the arch, gears on the rock ----------------------------------------------------------------
    decal(mb, "r212_clock", XC, YS + RO + 0.98, 1.5, 0.07)
    for cu, cv, dia, d in ((449.25, 2.75, 1.9, 0.05), (450.15, 4.55, 1.05, 0.08), (454.8, 2.35, 1.7, 0.05),
                           (455.35, 3.95, 1.0, 0.08), (453.55, 5.25, 0.8, 0.09)):
        decal(mb, "r212_gear", cu, cv, dia, d)

    # --- the ridge: the facade top is a knife edge; behind it a steep back slope (BACK_SLOPE from the ground) drops to
    # the stock tree row at z 736..737, which stays. The slope faces away from the fixed camera (steeper than its
    # 59 deg pitch), so it is always culled; it only closes the solid. Nothing rises into Hearthome City's view from
    # its south exit (the bottom of that screen sees ground up to z 735.4 and points at height y only when
    # z < 735.4 + 0.42 y; the ridge is at z 739.95, y 5.64). The east side is seen from the road.
    htop = G + VF * cs
    zt = ZF - VF * sn
    hb = G + VBAND * cs
    zb_ = ZF - VBAND * sn
    zback = zt - (htop - G) / math.tan(BACK_SLOPE)
    zbb = zt - (htop - hb) / math.tan(BACK_SLOPE)
    mb.face("r212_rock", [(X1, htop, zt), (X0, htop, zt), (X0, G, zback), (X1, G, zback)],
            [(0, 0), (4, 0), (4, 3), (0, 3)])
    # east side, faces +x: counter-clockwise seen from the east = z decreasing to the right
    for pts, mat in ((((X1, G, ZF), (X1, G, zback), (X1, hb, zbb), (X1, hb, zb_)), "r212_rock"),
                     (((X1, hb, zb_), (X1, hb, zbb), (X1, htop, zt)), "r212_rocktop")):
        uvs = [((ZF - p[2]) / 2, (htop - p[1]) / 2) for p in pts]
        mb.face(mat, list(pts), uvs)

    # --- the clearing: stone apron at the gate, a row of tall grass ------------------------------------------------
    mb.flat("r212_stone", CLEARING[0], 742.0, CLEARING[2], 743.0, G)
    mb.flat("r212_tallgr", CLEARING[0], 743.0, CLEARING[2], 744.0, G)       # tall grass: Klink by the gate


def tree_template(edit, centre=(449, 745)):
    """The 4 quads of the stock tree2_01 tree around centre (x, z), relative positions + UVs."""
    out = []
    for si, tex, pal in edit.iter_shapes():
        if tex != "tree2_01":
            continue
        tris, quads = edit._faces(si)
        for f in quads:
            pts = [edit.tile(v["pos"]) for v in f]
            cx = sum(p[0] for p in pts) / 4
            cz = sum(p[2] for p in pts) / 4
            if abs(cx - centre[0]) < 0.01 and centre[1] - 0.6 <= cz <= centre[1] + 0.01:
                w, h = 64, 64
                out.append(([(p[0] - centre[0], p[1], p[2] - centre[1]) for p in pts],
                            [(v["uv"][0] / (16 * w), v["uv"][1] / (16 * h)) for v in f]))
    assert len(out) == 4, f"tree template at {centre}: {len(out)} quads"
    return out


def build():
    edit = C.ChunkEdit(CHUNK_REL, CHUNK, BASE_REV)
    stock = {"tree": tree_template(edit)}

    def drop_tree(tex, pal, c, pts):
        x, h, z = c
        if X0 - 0.5 <= x < X1 + 0.5 and 737.5 <= z < ZF:         # trees inside the outcrop (rows 739, 741)
            return True
        return round(x) in (451, 453) and abs(x - round(x)) < 0.01 and ZF <= z < 743.1   # in front of the gate
    edit.drop(drop_tree, textures=TREE_TEX)
    edit.clip_flat(GROUND_TEX, [OUTCROP, CLEARING])

    _, set_bytes, _ = textures.build_set()
    tex_table, pal_names = C.texture_table(set_bytes)
    mb = C.MeshBuilder()
    build_gate(mb, stock)
    missing = sorted({m["texture"] for m in mb.materials.values()} - set(tex_table)) + \
        sorted({m["palette"] for m in mb.materials.values()} - pal_names)
    assert not missing, f"not in set 012 (run textures.py --write): {missing}"
    edit.add(mb, tex_table)
    model = edit.model_bytes()

    perm = edit.permissions()
    cx, cz = CHUNK
    for x in range(CLEARING[0], CLEARING[2]):
        for z in range(CLEARING[1], CLEARING[3]):
            perm[z - cz * 32][x - cx * 32] = TALL_GRASS if z == 743 else 0x0000
    data = edit.pack(perm, model)
    stats = edit.stats(model)
    stats["new_polygons"] = mb.polygons()
    return edit, data, model, perm, mb, stats


def gameplay_checks(edit, perm):
    import json as _json
    res = []
    cx, cz = CHUNK
    stock_perm = edit.permissions()
    walk = {}
    for z in range(32):
        for x in range(32):
            walk[(cx * 32 + x, cz * 32 + z)] = not perm[z][x] & 0x8000
    ev = _json.load(open(os.path.join(ROOT, "res/field/events/events_route_212_north.json")))
    for o in ev["object_events"]:
        if (o["x"], o["z"]) in walk and o["graphics_id"] not in ("OBJ_EVENT_GFX_POKEBALL",):
            walk[(o["x"], o["z"])] = False
    # flood from the gate warp's landing tile
    start = (458, 737)
    seen, todo = {start}, [start]
    while todo:
        x, z = todo.pop()
        for n in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if walk.get(n) and n not in seen:
                seen.add(n)
                todo.append(n)
    clear = [(x, z) for x in range(CLEARING[0], CLEARING[2]) for z in range(CLEARING[1], CLEARING[3])]
    res.append(("clearing tiles walkable and reachable from the Hearthome gate", all(t in seen for t in clear)))
    res.append(("outcrop tiles all blocked", all(not walk[(x, z)] for x in range(OUTCROP[0], OUTCROP[2])
                                                  for z in range(OUTCROP[1], OUTCROP[3]))))
    changed = [(cx * 32 + x, cz * 32 + z) for z in range(32) for x in range(32) if perm[z][x] != stock_perm[z][x]]
    res.append((f"only the clearing's permissions changed ({len(changed)} tiles)", sorted(changed) == sorted(clear)))
    b = mapdata.read_bdhc(edit.sec["bdhc"])
    hs = {round(mapdata.height_at(b, *mapdata.tile_centre(x - cx * 32, z - cz * 32)) / 4096, 3) for x, z in clear}
    res.append((f"clearing ground height = world y 32 like the road (BDHC stock): {sorted(hs)}", hs == {32.0}))
    return res


def main():
    edit, data, model, perm, mb, stats = build()
    print(json.dumps(stats, indent=1))
    ok = stats["model_bytes"] <= C.MODEL_BUFFER
    print(f"model {stats['model_bytes']} B (buffer {C.MODEL_BUFFER}) -> {'OK' if ok else 'TOO BIG'}")
    edited = {edit.model["shapes"][si]["name"] for si in edit.faces}
    bad = C.stock_shapes_identical(edit.model, edit.built, edited)
    print(("PASS " if not bad else "FAIL ") + f"untouched stock shapes and all stock materials byte-identical "
          f"(re-encoded after cuts: {sorted(edited)}) {bad}")
    ok &= not bad
    for name, good in gameplay_checks(edit, perm):
        print(("PASS " if good else "FAIL ") + name)
        ok &= good
    faces = C.camera_faces([(edit.built, CHUNK)])
    tiles = [(x, z) for x in range(448, 480) for z in range(736, 768)
             if not perm[z - 736][x - 448] & 0x8000]
    n, at = C.camera_polys(faces, tiles)
    sfaces = C.camera_faces([(edit.model, CHUNK)])
    n0, at0 = C.camera_polys(sfaces, tiles)
    print(f"camera polygons (chunk 085 only, CAMERA_TYPE_DEFAULT, every walkable tile): max {n} at {at} "
          f"(stock {n0} at {at0}); DS limit 2048")
    if "--mesh" in sys.argv:
        json.dump(mb.mesh("gate"), open(sys.argv[sys.argv.index("--mesh") + 1], "w"))
    if "--write" in sys.argv:
        assert ok, "refusing to write"
        open(os.path.join(ROOT, CHUNK_REL), "wb").write(data)
        print("wrote", CHUNK_REL, len(data), "B")


if __name__ == "__main__":
    main()
