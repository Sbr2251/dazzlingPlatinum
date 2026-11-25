#!/usr/bin/env python3
"""Terrain dressing for the Solaceon Ruins raid: the excavation at the Room 1 entrance and the vault in Room 7.

Usage:
  python3 tools/solaceon_ruins/build_dressing.py                    dry run: budgets + checks
  python3 tools/solaceon_ruins/build_dressing.py --preview DIR      also decode the result to mesh.json and render the
                                                                    two rooms (top + CAMERA_TYPE_CAVE), with the raid
                                                                    objects as billboards, into DIR
  python3 tools/solaceon_ruins/build_dressing.py --write            write map_data_390 and map_data_405
                                                                    (run textures.py --write first)

Inputs: the stock chunks and set 055 at ruins.BASE_REV (read from git; re-running never feeds back) and textures.py.
The chunks are edited in place (tools/world_art/chunkedit.py): every stock shape and material stays byte for byte,
the dressing is appended as new materials and shapes. Lit like stock: these rooms' stock materials are unlit
(lights 0) with baked vertex shades (205 tops, 156 mid slopes, 98 feet), and so are the new ones.

Only chunks used by exactly one map header are edited (checked against the headers' matrices):
  map_data_390  MAP_HEADER_SOLACEON_RUINS_ROOM_1   scaffold towers + work lights in the two entrance corners,
                                                   a warm light pool, a cable run from the entrance to the stair
                                                   down to Room 2. Permissions: (4,11) and (6,11) become blocked
                                                   (the towers). BDHC and props unchanged.
  map_data_405  MAP_HEADER_SOLACEON_RUINS_ROOM_7   the shard-machine plinth at (5,11) (blocked), cables from the
                                                   entry stair to the plinth and on to the west racks, violet-lit
                                                   floor cracks, a fresh tunnel mouth in the west wall at z 10 with
                                                   loose rubble at its foot. Permissions: (5,11) becomes blocked.
                                                   BDHC and props unchanged.
Terrain is permanent in every story state; everything that must come and go is an object event (placements.py).
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import placements as PL  # noqa: E402
import ruins as R  # noqa: E402
import textures as T  # noqa: E402

sys.path.insert(0, os.path.join(R.ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402

BASE_REV = R.BASE_REV
SHADE = {"up": 205, "s": 176, "e": 156, "w": 156, "n": 120, "down": 98}
BLOCK = 0x8000

# CAMERA_TYPE_CAVE (field_camera.c), for the on-screen polygon count
CAVE_PITCH, CAVE_DIST, CAVE_HALF_FOV = 63.2647705078125, 574.577880859375, 9.4976806640625


# --------------------------------------------------------------------------------------------------------------
# geometry helpers (absolute tiles x, h, z; the Ruins floor is h 0)
# --------------------------------------------------------------------------------------------------------------

def quad(mb, mat, pts, uvs, want, shade=None):
    """A quad whose front faces `want` (a rough outward direction); the winding is flipped if needed."""
    n = C.face_normal(pts)
    if sum(a * b for a, b in zip(n, want)) < 0:
        pts, uvs = pts[::-1], uvs[::-1]
        n = C.face_normal(pts)
    if shade is None:
        if n[1] > 0.7:
            shade = SHADE["up"]
        elif n[1] < -0.7:
            shade = SHADE["down"]
        elif abs(n[2]) >= abs(n[0]):
            shade = SHADE["s"] if n[2] > 0 else SHADE["n"]
        else:
            shade = SHADE["e"]
    mb.face(mat, pts, uvs, color=(shade, shade, shade))


def floor_decal(mb, mat, x0, z0, x1, z1, h, flip_u=False, flip_v=False, uv=(1.0, 1.0)):
    u0, u1 = (uv[0], 0.0) if flip_u else (0.0, uv[0])
    v0, v1 = (uv[1], 0.0) if flip_v else (0.0, uv[1])
    quad(mb, mat, [(x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0)], [(u0, v1), (u1, v1), (u1, v0), (u0, v0)],
         (0, 1, 0), SHADE["up"])


def box(mb, side, top, x0, x1, z0, z1, h0, h1, faces=("up", "s", "e", "w", "n"), tile_uv=True):
    """Axis-aligned box; UVs one repeat per tile (so 16-texel textures keep the stock density)."""
    if "up" in faces:
        quad(mb, top, [(x0, h1, z1), (x1, h1, z1), (x1, h1, z0), (x0, h1, z0)],
             [(0, z1 - z0), (x1 - x0, z1 - z0), (x1 - x0, 0), (0, 0)] if tile_uv else [(0, 1), (1, 1), (1, 0), (0, 0)],
             (0, 1, 0))
    hh = h1 - h0
    if "s" in faces:
        quad(mb, side, [(x0, h0, z1), (x1, h0, z1), (x1, h1, z1), (x0, h1, z1)],
             [(0, hh), (x1 - x0, hh), (x1 - x0, 0), (0, 0)], (0, 0, 1))
    if "n" in faces:
        quad(mb, side, [(x1, h0, z0), (x0, h0, z0), (x0, h1, z0), (x1, h1, z0)],
             [(0, hh), (x1 - x0, hh), (x1 - x0, 0), (0, 0)], (0, 0, -1))
    if "e" in faces:
        quad(mb, side, [(x1, h0, z1), (x1, h0, z0), (x1, h1, z0), (x1, h1, z1)],
             [(0, hh), (z1 - z0, hh), (z1 - z0, 0), (0, 0)], (1, 0, 0))
    if "w" in faces:
        quad(mb, side, [(x0, h0, z0), (x0, h0, z1), (x0, h1, z1), (x0, h1, z0)],
             [(0, hh), (z1 - z0, hh), (z1 - z0, 0), (0, 0)], (-1, 0, 0))


def cable(mb, mat, pts, h=0.03, w=0.5):
    """A cable strip along an axis-aligned polyline [(x, z), ...]; texture u along the run (2 tiles per repeat),
    v across. Each segment sits a hair higher than the last so the corner overlaps never z-fight."""
    run = 0.0
    for i, ((ax, az), (bx, bz)) in enumerate(zip(pts, pts[1:])):
        hh = h + 0.004 * (i % 2)
        L = abs(bx - ax) + abs(bz - az)
        u0, u1 = run / 2.0, (run + L) / 2.0
        r = w / 2
        if az == bz:          # along x
            x0, x1 = min(ax, bx) - (r if i else 0), max(ax, bx) + (r if i < len(pts) - 2 else 0)
            if bx < ax:
                x0, x1 = min(ax, bx) - (r if i < len(pts) - 2 else 0), max(ax, bx) + (r if i else 0)
            p = [(x0, hh, az + r), (x1, hh, az + r), (x1, hh, az - r), (x0, hh, az - r)]
            uv = [(u0, 1), (u1, 1), (u1, 0), (u0, 0)] if bx >= ax else [(u1, 1), (u0, 1), (u0, 0), (u1, 0)]
        else:                 # along z
            z0, z1 = min(az, bz), max(az, bz)
            p = [(ax - r, hh, z1), (ax + r, hh, z1), (ax + r, hh, z0), (ax - r, hh, z0)]
            uv = [(u1, 0), (u1, 1), (u0, 1), (u0, 0)] if bz >= az else [(u0, 0), (u0, 1), (u1, 1), (u1, 0)]
        quad(mb, mat, p, uv, (0, 1, 0), SHADE["up"])
        run += L


def wall_decal_west(mb, mat, profile, z0, z1, eps=0.03):
    """A decal following a west wall's stock profile [(x, h) from the floor up], pushed eps out along each segment's
    normal (into the room). u runs along z (0..1 over z0..z1), v from the top (0) to the floor (1)."""
    segs = list(zip(profile, profile[1:]))
    lens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs]
    tot = sum(lens)
    acc = 0.0
    off = []
    for (a, b) in segs:
        dx, dh = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dh)
        nx, nh = dh / L, -dx / L          # rotate the up-the-wall direction: points into the room (+x) and up
        if nx < 0:
            nx, nh = -nx, -nh
        off.append((nx * eps, nh * eps))
    for i, ((a, b), L) in enumerate(zip(segs, lens)):
        ox, oh = off[i]
        va, vb = 1 - acc / tot, 1 - (acc + L) / tot
        pa = (a[0] + ox, a[1] + oh)
        pb = (b[0] + ox, b[1] + oh)
        quad(mb, mat, [(pa[0], pa[1], z1), (pa[0], pa[1], z0), (pb[0], pb[1], z0), (pb[0], pb[1], z1)],
             [(1, va), (0, va), (0, vb), (1, vb)], (1, 0.5, 0), 205 if i in (0, 3) else (156 if i in (1, 4) else 120))
        acc += L


# --------------------------------------------------------------------------------------------------------------
# the two rooms
# --------------------------------------------------------------------------------------------------------------

def materials(mb, names):
    tm = T.materials()
    for n in names:
        tex, pal, size = tm[n]
        mb.material("rr_" + n[3:], tex, pal, size, lights=0)
    return {n: "rr_" + n[3:] for n in names}


def dress_room1(mb):
    M = materials(mb, ["rd_scaff", "rd_plank", "rd_steel", "rd_lamp", "rd_crate", "rd_cable", "rd_glow"])
    # the warm pool first (lowest), then the cable over it
    floor_decal(mb, M["rd_glow"], 4.0, 7.6, 7.0, 11.0, 0.015)
    cable(mb, M["rd_cable"], [(6.72, 10.95), (6.72, 3.5), (7.06, 3.5)], h=0.03, w=0.42)
    cable(mb, M["rd_cable"], [(4.94, 10.9), (6.06, 10.9)], h=0.038, w=0.36)
    for x0, x1, inner in ((4.06, 4.94, "e"), (6.06, 6.94, "w")):
        z0, z1 = 11.06, 11.94
        # scaffold faces: south (towards the camera), the inner side (towards the exit), the outer side
        quad(mb, M["rd_scaff"], [(x0, 0, z1), (x1, 0, z1), (x1, 2.0, z1), (x0, 2.0, z1)],
             [(0, 1), (1, 1), (1, 0), (0, 0)], (0, 0, 1))
        for x, want in ((x1, (1, 0, 0)), (x0, (-1, 0, 0))):
            quad(mb, M["rd_scaff"], [(x, 0, z1), (x, 0, z0), (x, 2.0, z0), (x, 2.0, z1)],
                 [(0, 1), (1, 1), (1, 0), (0, 0)], want)
        # boards at h 1.0 and 2.0 (top + a thin south edge)
        for hb in (1.0, 2.0):
            box(mb, M["rd_plank"], M["rd_plank"], x0, x1, z0, z1, hb - 0.06, hb, faces=("up", "s"))
        # the work lamp on the top boards, its lens tipped down towards the room (north)
        lx0, lx1 = (x0 + 0.14, x1 - 0.14)
        box(mb, M["rd_steel"], M["rd_steel"], lx0 + 0.2, lx1 - 0.2, 11.5, 11.7, 2.0, 2.3, faces=("s", "e", "w"))
        box(mb, M["rd_steel"], M["rd_steel"], lx0, lx1, 11.36, 11.76, 2.3, 2.62, faces=("up", "s", "e", "w"))
        # the lens, aimed up and into the room (north); tipped back far enough that the camera (63 deg pitch,
        # from the south) sees its face: normal (0, 0.8, -0.6)
        quad(mb, M["rd_lamp"], [(lx0, 2.62, 11.36), (lx1, 2.62, 11.36), (lx1, 2.92, 11.76), (lx0, 2.92, 11.76)],
             [(0, 0), (1, 0), (1, 1), (0, 1)], (0, 0.8, -0.6), 205)
    # crates in the towers' feet (the tiles are blocked)
    box(mb, M["rd_crate"], M["rd_crate"], 4.16, 4.78, 11.22, 11.86, 0.0, 0.58)
    box(mb, M["rd_crate"], M["rd_crate"], 6.22, 6.74, 11.3, 11.84, 0.0, 0.46)
    box(mb, M["rd_crate"], M["rd_crate"], 6.3, 6.68, 11.38, 11.76, 0.46, 0.8)


R7_WEST_PROFILE = [(2.0, 0.0), (1.75, 0.125), (1.25, 0.875), (1.0, 1.0), (0.75, 1.125), (0.25, 1.875), (0.0, 2.0)]


def dress_room7(mb):
    M = materials(mb, ["rd_steel", "rd_plate", "rd_cable", "rd_crack", "rd_tunnel", "rd_rubble"])
    # violet-lit cracks spreading from the plinth (under everything else)
    floor_decal(mb, M["rd_crack"], 4.0, 9.5, 6.0, 11.5, 0.018)
    floor_decal(mb, M["rd_crack"], 2.3, 8.5, 4.3, 10.5, 0.020, flip_u=True)
    floor_decal(mb, M["rd_crack"], 6.1, 7.4, 8.1, 9.4, 0.022, flip_v=True)
    # loose rubble at the tunnel's foot
    floor_decal(mb, M["rd_rubble"], 2.0, 9.6, 3.0, 10.6, 0.026)
    floor_decal(mb, M["rd_rubble"], 2.0, 10.5, 2.8, 11.3, 0.027, flip_u=True, uv=(0.8, 0.8))
    # cables: entry stair -> down the east side -> the plinth; the plinth -> the west racks
    cable(mb, M["rd_cable"], [(9.0, 3.5), (7.5, 3.5), (7.5, 11.5), (5.95, 11.5)], h=0.032, w=0.46)
    cable(mb, M["rd_cable"], [(5.05, 11.5), (3.5, 11.5), (3.5, 6.5), (2.55, 6.5)], h=0.032, w=0.46)
    # the plinth: a low steel skirt and the machine body with the shard socket on top
    box(mb, M["rd_steel"], M["rd_steel"], 5.02, 5.98, 11.02, 11.98, 0.0, 0.12, faces=("up", "s", "e", "w", "n"))
    box(mb, M["rd_steel"], M["rd_plate"], 5.12, 5.88, 11.12, 11.88, 0.12, 0.62, tile_uv=False)
    # the fresh tunnel in the west wall, centred on z 10.3 (Indra leaves from (2,10) walking west)
    wall_decal_west(mb, M["rd_tunnel"], R7_WEST_PROFILE, 9.5, 11.1)


ROOMS = {
    390: dict(header="ROOM_1", dress=dress_room1, blocked=[(4, 11), (6, 11)]),
    405: dict(header="ROOM_7", dress=dress_room7, blocked=[(5, 11)]),
}


# --------------------------------------------------------------------------------------------------------------
# build + checks
# --------------------------------------------------------------------------------------------------------------

def git_files(rev, rels):
    """Several files at rev in one `cat-file --batch` call -> {rel: bytes or None}."""
    import subprocess
    inp = "".join(f"{rev}:{r}\n" for r in rels).encode()
    out = subprocess.run(["git", "-C", R.ROOT, "cat-file", "--batch"], input=inp, capture_output=True,
                         check=True).stdout
    res, i = {}, 0
    for r in rels:
        nl = out.index(b"\n", i)
        head = out[i:nl].split()
        if head[-1] == b"missing":
            res[r] = None
            i = nl + 1
            continue
        n = int(head[2])
        res[r] = out[nl + 1:nl + 1 + n]
        i = nl + 1 + n + 1
    return res


def _matrices():
    rels = [f"res/field/maps/matrices/map_matrix_{i:03d}.json" for i in range(400)]
    got = git_files(BASE_REV, rels)
    return {i: json.loads(got[r]) for i, r in enumerate(rels) if got[r] is not None}


def chunk_users(mtx=None):
    """chunk id -> {map headers} from map_headers.h and the matrices (at BASE_REV)."""
    mtx = mtx or _matrices()
    src = C.git_file(BASE_REV, "include/data/map_headers.h").decode()
    users = {}
    for m in re.finditer(r'\[(MAP_HEADER_\w+)\] = \{(.*?)\n    \},', src, re.S):
        mid = int(re.search(r'\.mapMatrixID = ([^,]+),', m.group(2)).group(1), 0)
        for row in mtx.get(mid, {}).get("maps", []):
            for name in row:
                if re.fullmatch(r"MAP_\d+", name):
                    users.setdefault(int(name[4:]), set()).add(m.group(1))
    return users


def all_matrix_users(mtx=None):
    """chunk id -> {matrices that reference it} (any matrix, with or without a header)."""
    mtx = mtx or _matrices()
    out = {}
    for i, d in mtx.items():
        for row in d["maps"]:
            for name in row:
                if re.fullmatch(r"MAP_\d+", name):
                    out.setdefault(int(name[4:]), set()).add(i)
    return out


def build(chunk):
    spec = ROOMS[chunk]
    edit = C.ChunkEdit(R.chunk_rel(chunk), (0, 0), BASE_REV)
    _, set_bytes, _ = T.build_set()
    tex_table, pal_names = C.texture_table(set_bytes)
    mb = C.MeshBuilder()
    spec["dress"](mb)
    missing = sorted({m["texture"] for m in mb.materials.values()} - set(tex_table)) + \
        sorted({m["palette"] for m in mb.materials.values()} - pal_names)
    assert not missing, f"not in set 055: {missing}"
    edit.add(mb, tex_table)
    model = edit.model_bytes()
    perm = edit.permissions()
    for x, z in spec["blocked"]:
        perm[z][x] = BLOCK
    data = edit.pack(perm, model)
    stats = edit.stats(model)
    stats["new_polygons"] = mb.polygons()
    return edit, data, model, perm, mb, stats


def cave_polys(model, tiles):
    # chunkedit.camera_polys aims at world y 32 (the overworld ground); the Ruins floor is y 16, so lift by 16
    faces = [([(p[0], p[1] + 16.0, p[2]) for p in pts], ds) for pts, ds in C.camera_faces([(model, (0, 0))])]
    saved = (C.PITCH, C.DIST, C.HALF_FOV)
    C.PITCH, C.DIST, C.HALF_FOV = CAVE_PITCH, CAVE_DIST, CAVE_HALF_FOV
    try:
        return C.camera_polys(faces, tiles)
    finally:
        C.PITCH, C.DIST, C.HALF_FOV = saved


def checks(chunk, edit, data, model, perm, stats, users, mtx_users):
    spec = ROOMS[chunk]
    res = []
    hdrs = users.get(chunk, set())
    res.append((f"map_data_{chunk} is used by exactly one map header ({sorted(hdrs)}) and one matrix "
                f"({sorted(mtx_users.get(chunk, ()))})",
                hdrs == {"MAP_HEADER_SOLACEON_RUINS_" + spec["header"]} and len(mtx_users.get(chunk, ())) == 1))
    stock = mapdata.read_permissions(edit.sec["permissions"])
    diff = [(x, z, stock[z][x], perm[z][x]) for z in range(32) for x in range(32) if stock[z][x] != perm[z][x]]
    res.append((f"permissions: only the intended tiles change: "
                + ", ".join(f"({x},{z}) 0x{a:04x}->0x{b:04x}" for x, z, a, b in diff),
                sorted((x, z) for x, z, _, _ in diff) == sorted(spec["blocked"])
                and all(a == 0x0008 for _, _, a, _ in diff)))
    res.append(("blocked tiles match placements.INTENDED_BLOCKED",
                set(spec["blocked"]) == PL.INTENDED_BLOCKED.get(spec["header"], set())))
    sec = mapdata.unpack(data)
    res.append(("BDHC byte-identical to stock", sec["bdhc"] == edit.sec["bdhc"]))
    res.append(("props byte-identical to stock", sec["props"] == edit.sec["props"]))
    edited = {edit.model["shapes"][si]["name"] for si in edit.faces}
    bad = C.stock_shapes_identical(edit.model, edit.built, edited)
    res.append((f"every stock shape and material byte-identical (stock shapes re-encoded: {sorted(edited) or 'none'})",
                not bad and not edited))
    res.append((f"model {stats['model_bytes']} B <= 0xF000 ({C.MODEL_BUFFER})", stats["model_bytes"] <= C.MODEL_BUFFER))
    res.append((f"polygons {stats['stock_polygons']} -> {stats['polygons']} (soft budget 1000)",
                stats["polygons"] <= 1000))
    # every walkable tile: the new geometry never rises over a tile the player can stand on, except decals
    tops = []
    mesh = nsbmd.model_to_mesh(edit.built, (0, 0))
    mats = {m["name"]: m for m in mesh["materials"]}
    for me in mesh["meshes"]:
        if not me["material"].startswith("rr_"):
            continue
        P = me["positions"]
        for f in me["quads"] + me["tris"]:
            pts = [P[i] for i in f]
            if max(p[1] for p in pts) > 0.05:
                cx = sum(p[0] for p in pts) / len(pts)
                cz = sum(p[2] for p in pts) / len(pts)
                tops.append((int(math.floor(cx)), int(math.floor(cz)), me["material"]))
    walk = {(x, z) for z in range(32) for x in range(32) if not perm[z][x] & BLOCK}
    over = sorted({(x, z) for x, z, _ in tops if (x, z) in walk})
    res.append((f"no raised dressing over a walkable tile (by face centroid): {over or 'none'}", not over))
    tiles = sorted(walk)
    n, at = cave_polys(edit.built, tiles)
    n0, _ = cave_polys(edit.model, tiles)
    res.append((f"on screen (CAMERA_TYPE_CAVE, every walkable tile): stock {n0} -> {n} polygons at {at} (limit 1800)",
                n <= 1800))
    return res


def preview(d, built):
    """Decoded meshes + stock dump + new textures + billboards, rendered with Blender (top + cave views)."""
    import survey
    import billboards
    stock = os.path.join(d, "stock")
    if not os.path.exists(os.path.join(stock, "textures", "dun_floor.png")):
        survey.dump(stock)
    tex_new = os.path.join(d, "textures")
    T.preview(tex_new, T.build_textures())
    mesh_dir = os.path.join(d, "dressed")
    os.makedirs(mesh_dir, exist_ok=True)
    for ch in sorted({v[2] for v in R.ROOMS.values()}):
        src = os.path.join(stock, f"chunk_{ch}.mesh.json")
        dst = os.path.join(mesh_dir, f"chunk_{ch}.mesh.json")
        if ch in built:
            json.dump(nsbmd.model_to_mesh(built[ch], (0, 0), name=f"chunk_{ch}"), open(dst, "w"))
        else:
            open(dst, "w").write(open(src).read())
    spr_dir = os.path.join(d, "sprites")
    target = {"R1": (5, 7.5), "R7": (5, 7)}
    plan = [("pre", ["R1"]), ("raid", ["R1", "R7", "R1-NW", "R2", "R2-NE", "R3", "R4", "R4-SE", "R5", "R6", "R6-NW"]),
            ("vault", ["R7"]), ("after", ["R1", "R7"])]
    for state, rooms in plan:
        for mode in ("game", "top"):
            files = billboards.write_room_billboards(mesh_dir, spr_dir, state, mode)
            survey.render(stock, mesh_dir=mesh_dir, rooms=rooms, tag="_" + state, extra_tex=[tex_new, spr_dir],
                          px=32, extra_files={k: [v] for k, v in files.items()}, dest=d, target=target, views=mode)
    names = ["R1_pre", "R1_raid", "R1_after", "R2_raid", "R2-NE_raid", "R3_raid", "R4_raid", "R4-SE_raid", "R5_raid",
             "R6_raid", "R6-NW_raid", "R7_raid", "R7_vault", "R7_after", "R1-NW_raid"]
    survey.contact_sheet([os.path.join(d, n + "_game.png") for n in names], os.path.join(d, "raid_game_sheet.png"),
                         cols=5, shrink=3)
    survey.contact_sheet([os.path.join(d, n + "_top.png") for n in ("R7_raid", "R7_vault", "R7_after")],
                         os.path.join(d, "raid_r7_top_sheet.png"), cols=3, shrink=1)
    survey.contact_sheet([os.path.join(d, n + "_top.png") for n in ("R1_pre", "R1_raid", "R1_after")],
                         os.path.join(d, "raid_r1_top_sheet.png"), cols=3, shrink=1)
    print("renders in", d, "; sheets raid_game_sheet.png (order:", ", ".join(names) + "), raid_r1_top_sheet.png,"
          " raid_r7_top_sheet.png")


def main():
    mtx = _matrices()
    users = chunk_users(mtx)
    mtx_users = all_matrix_users(mtx)
    ok = True
    built = {}
    out = {}
    for chunk in ROOMS:
        edit, data, model, perm, mb, stats = build(chunk)
        built[chunk] = edit.built
        out[chunk] = data
        print(f"== map_data_{chunk} ({ROOMS[chunk]['header']})")
        print(json.dumps(stats))
        for name, good in checks(chunk, edit, data, model, perm, stats, users, mtx_users):
            print(("PASS " if good else "FAIL ") + name)
            ok &= good
    if "--preview" in sys.argv:
        preview(sys.argv[sys.argv.index("--preview") + 1], built)
    if "--write" in sys.argv:
        assert ok, "refusing to write"
        cur = open(os.path.join(R.ROOT, T.SET_REL), "rb").read()
        assert cur == T.build_set()[1], "set 055 in the tree is not textures.py's output: run textures.py --write"
        for chunk, data in out.items():
            open(os.path.join(R.ROOT, R.chunk_rel(chunk)), "wb").write(data)
            print("wrote", R.chunk_rel(chunk), len(data), "B")
    print("ALL PASS" if ok else "SOME CHECKS FAILED")


if __name__ == "__main__":
    main()
