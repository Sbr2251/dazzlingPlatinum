#!/usr/bin/env python3
"""Builds the land data of DW Ravaged Path (MAP_HEADER_DW_RAVAGED_PATH, matrix 291, map_data_669/670).

The map is the Arc 1 seams floor (map_data_667/668, built by build_arc1_seams_map.py from DW B1F). The BDHC is
copied unchanged; the permissions change so the walkable tiles match what the model draws, and the model gains the
scar decals (owner playtest round 2, fix2-dwrp):

- In Arc 1, Barry stood at (21,12), east of the entry, and closed the walkway's east end. Ravaged Path has no
  Barry, so the player could walk right off the entry: the stepping stones (25,12) and (28,12) are drawn (ghost
  props), but B1F's hop tiles (29..30,12) then jumped the player to (31,12), where nothing is drawn (an invisible
  ledge). The hop tiles past the last stone lose their jump behaviour and stay blocked, so (28,12) is a dead end.
  The same for the lower chain's last hop (30..31,22), which jumps into the all-blocked 670 block.
- The chasm-lip rows next to the walkway fall (coord events, the fall script), but some lip tiles are drawn
  ground: (16..19,13) is the floor under the two trees south of the walkway, and (16..18,11) is the rock block
  north of it. Stepping there dropped the player while they stood on solid-looking ground. Those tiles are
  blocked again, as in stock B1F. The lips that are open void stay walkable (and fall): (15,11), (19..21,11),
  (20..21,13), (12..15,15). Keep in sync with res/field/events/events_dw_ravaged_path.json.

- The SCARS on the west wall (Arc2DwRavagedPath_HandleStep in src/overlay009/ov9_02249960.c) were drawn exactly like
  the rest of the wall face, so their falls looked like falls from solid wall. Each scar tile now carries a decal:
  the DW texture s_land4 (a loose boulder on the pink ground; texture set 73, shared by every DW map) on a quad a
  hair in front of the wall face (x = 11). The wall face draws grid column z (tools/distortion_world/
  ravaged_path.json) at model z+1..z+2 and grid row y at model y-0.5..y+0.5 (the trees: grid z 15-18, y 3-4 are
  drawn at z 16-20, y 2.5-4.5). Keep SCAR_TILES in sync with sRavagedPathScarTiles and the spec's "scars".

- The SIGIL (2,14) and the BRIDGES (2,15), (4,20), (4,21) get the same treatment (dwp:rift-rp): the sigil tile
  carries an s_land3 decal (blue diamonds on pink: a glowing rune marking, distinct from the wall and the boulder),
  and each bridge tile carries an s_land2 decal (flat black: a dark empty socket, i.e. "no ground here", not drawn
  ground). When a bridge is on, its ghost-prop stone sits in the socket. Keep RUNE_TILE / BRIDGE_TILES in sync with
  src/overlay009/dw_puzzle_ravaged_path.c.

Tile coordinates are DW world tiles (the map sits at DW offset (0,0,0)): x 0-31 is 669, x 32-63 is 670.

Usage: python3 tools/distortion_world/build_ravaged_path_map.py [--check]
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import mapdata  # noqa: E402
import nsbmd  # noqa: E402

DATA = os.path.join(ROOT, "res/field/maps/data")
SRC = {669: 667, 670: 668}
BLOCKED = 0x8000

# (x0, z0, x1, z1) inclusive: set to plain blocked (no tile behaviour).
BLOCK = [
    (29, 12, 30, 12),   # the hop off the last upper stepping stone (28,12) onto the undrawn (31,12)
    (30, 22, 31, 22),   # the hop off the last lower stepping stone (29,22) into the 670 block
    (16, 13, 19, 13),   # drawn ground under the two trees south of the walkway (was a falling lip)
    (16, 11, 18, 11),   # the drawn rock block north of the walkway (was a falling lip)
]


# Scar tiles (grid y, grid z), as in sRavagedPathScarTiles.
SCAR_TILES = [(2, 16), (2, 20), (2, 21), (3, 20), (3, 21)]
# Sigil tile (grid y, grid z), as in dw_puzzle_ravaged_path.c: the SET
# sigil that switches bridge group 0 ON.
RUNE_TILE = (2, 14)
# Bridge tiles (grid y, grid z), as in dw_puzzle_ravaged_path.c group 0.
BRIDGE_TILES = [(2, 15), (4, 20), (4, 21)]
WALL_X = 11.0
DECAL_DX = 0.03            # tiles in front of the face (about half a world unit)


def add_wall_decals(model_bytes):
    """Appends one material + shape per decal set (scar, rune, socket) to the chunk model; the rest is unchanged."""
    for tiles, texture, suffix in ((SCAR_TILES, "s_land4", "scar"),
                                   ([RUNE_TILE], "s_land3", "rune"),
                                   (BRIDGE_TILES, "s_land2", "socket")):
        model_bytes = add_decals(model_bytes, tiles, texture, suffix)
    return model_bytes


def add_decals(model_bytes, tiles, texture, suffix):
    """Appends one material + shape (decals for `tiles`) to the chunk model; the rest of the model is unchanged."""
    bmd = nsbmd.parse_bmd(model_bytes)
    m = bmd["models"][0]
    assert all(x["name"] != texture + "_" + suffix for x in m["materials"]), "decals already present"
    pos, uvs, quads = [], [], []
    for gy, gz in tiles:
        x, z0, y0 = WALL_X + DECAL_DX, gz + 1, gy - 0.5
        k = len(pos)
        # same corner order and UVs as the stock wall-face quads (front face +x)
        pos += [[x, y0 + 1, z0 + 1], [x, y0, z0 + 1], [x, y0, z0], [x, y0 + 1, z0]]
        uvs += [[0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]
        quads.append([k, k + 1, k + 2, k + 3])
    mat = {"name": texture + "_" + suffix, "texture": texture, "palette": texture, "size": [16, 16],
           "repeat": [True, True]}
    mesh = {"name": suffix, "materials": [mat],
            "meshes": [{"material": mat["name"], "positions": pos, "uvs": uvs, "normals": [[1.0, 0.0, 0.0]] * len(pos),
                        "tris": [], "quads": quads}]}
    dm = nsbmd.mesh_to_model(mesh, (0, 0), pos_scale=m["info"]["pos_scale"])
    mi, si = len(m["materials"]), len(m["shapes"])
    m["materials"].append(dm["materials"][0])
    shape = dm["shapes"][0]
    shape["name"] = "polygon%d" % si
    m["shapes"].append(shape)
    end = m["sbc"].index("2b")
    m["sbc"][end:end] = ["04%02x" % mi, "05%02x" % si]
    for key in ("tex_bind", "pltt_bind"):
        # s_land3 is already bound by a stock wall material: merge the new
        # material into the existing entry instead of adding a second
        # entry with the same name (the name dictionary cannot hold
        # duplicates). s_land2 / s_land4 have no stock entry: append one.
        existing = next((b for b in m[key] if b["name"] == texture), None)
        if existing is None:
            m[key].append({"name": texture, "mats": [mi], "flag": m[key][0].get("flag", 0)})
        elif mi not in existing["mats"]:
            existing["mats"].append(mi)
        m[key].sort(key=lambda b: b["name"])
    for k in ("num_vertex", "num_polygon", "num_triangle", "num_quad"):
        m["info"][k] += dm["info"][k]
    m["info"]["num_mat"] += 1
    m["info"]["num_shp"] += 1
    return nsbmd.build_bmd(bmd["models"], bmd["tex0"], bmd["version"])


def build():
    out = {}
    for dst, src in SRC.items():
        parts = mapdata.unpack(open(os.path.join(DATA, f"map_data_{src}.bin"), "rb").read())
        perm = mapdata.read_permissions(parts["permissions"])
        x_base = 0 if dst == 669 else 32
        for x0, z0, x1, z1 in BLOCK:
            for z in range(z0, z1 + 1):
                for x in range(x0, x1 + 1):
                    if x_base <= x < x_base + 32:
                        perm[z][x - x_base] = BLOCKED
        parts["permissions"] = mapdata.write_permissions(perm)
        model = add_wall_decals(parts["model"]) if dst == 669 else parts["model"]
        out[dst] = mapdata.pack(parts["permissions"], parts["props"], model, parts["bdhc"])
    return out


def main():
    out = build()
    check = "--check" in sys.argv
    ok = True
    for dst, data in out.items():
        path = os.path.join(DATA, f"map_data_{dst}.bin")
        same = os.path.exists(path) and open(path, "rb").read() == data
        ok &= same
        if not check:
            open(path, "wb").write(data)
            print(path, "unchanged" if same else "written")
    if check:
        print("OK" if ok else "map_data differs (run without --check)")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
