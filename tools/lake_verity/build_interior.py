#!/usr/bin/env python3
"""Builds Verity Castle 1F (the entrance hall) from the art export. Standard library only.

Usage: python3 tools/lake_verity/build_interior.py [--write] [--preview <dir>]

Inputs:
  tools/lake_verity/assets/interior_1f/interior_1f.mesh.json  (made by ~/Documents/Lake Verity Update/art/lv_interior.py)
  tools/lake_verity/assets/textures/<name>.png/.json          (only the textures the room uses)
  tools/lake_verity/interior_layout.py                        (collision, heights, warps, exit mat)

Outputs (--write):
  res/field/maps/data/map_data_666.bin            permissions + exit mat prop + NSBMD + BDHC
  res/field/maps/texture_sets/map_texture_set_075.nsbtx
  res/field/maps/matrices/map_matrix_289.json     1 x 1: [["MAP_666"]]
  area_data.narc entry 76 (0x4C)                  props list 21 (the minimal indoor list with d_mat01, the stock
                                                  exit mat), texture set 75, light 1 (indoor)
  and their registrations: map_data meson.build + map_data.order + generated/maps.txt (MAP_666), matrices
  meson.build + map_matrices.order, texture_sets meson.build + map_texture_set.order.
  Re-running is idempotent (registrations are only added once, the area entry is rewritten in place).

Checks (always): mesh -> NSBMD -> decode gives the same faces; NSBTX parse -> build identical and every texture
decodes to its PNG; map_data unpack -> pack identical; permissions and BDHC (height at every tile centre) match
interior_layout; budgets (model buffer, polygons, VRAM).
--preview writes the decoded map model and the exit mat prop as mesh.json (plus the textures) for blender_preview.py.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "coronet_lava"))

import assemble  # noqa: E402
import interior_layout as IL  # noqa: E402
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import png  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
ASSET = os.path.join(HERE, "assets", "interior_1f", "interior_1f.mesh.json")
TEXDIR = os.path.join(HERE, "assets", "textures")
MAPS = os.path.join(ROOT, "res", "field", "maps", "data")
MATRICES = os.path.join(ROOT, "res", "field", "maps", "matrices")
TEXSETS = os.path.join(ROOT, "res", "field", "maps", "texture_sets")
AREA_DATA = os.path.join(ROOT, "res", "prebuilt", "fielddata", "areadata", "area_data.narc")
AREA_BUILD = os.path.join(ROOT, "res", "prebuilt", "fielddata", "areadata", "area_build_model", "area_build.narc")
BUILD_MODEL = os.path.join(ROOT, "res", "prebuilt", "fielddata", "build_model", "build_model.narc")
MAPS_TXT = os.path.join(ROOT, "generated", "maps.txt")

MAP_ID = 666
MATRIX_ID = 289
SET_ID = 75
AREA_ID = 0x4C
PROPS_LIST = 21              # area_build list [78 d_mat01, 152 object01] (stock: area 0x19, Oreburgh Gym)
AREA_LIGHT = 1               # indoor area light, as the Old Chateau (area 66: props 62, set 65, light 1)
MODEL_NAME = "vcastle_1f"
MATRIX_NAME = "m_vcastle1"
FX = 4096


def texture_meta(name):
    p = os.path.join(TEXDIR, name + ".json")
    return json.load(open(p)) if os.path.exists(p) else {}


def build_texset(names):
    tex, pals = nsbtx.load_texture_dir(TEXDIR, names)
    table = {}
    for t in tex:
        meta = texture_meta(t["name"])
        table[t["name"]] = {"size": [t["w"], t["h"]], "palette": meta.get("palette", t["name"] + "_pl"),
                            "repeat": meta.get("repeat", [True, True]), "format": nsbtx.FMT_NAMES[t["fmt"]]}
    return nsbtx.build(tex, pals), table


def exit_mat_prop():
    x, z = IL.EXIT_TILE
    return {"model": IL.EXIT_MAT_MODEL, "pos": [int((x + 0.5 - 16) * 16 * FX), 0, int((z + 0.5 - 16) * 16 * FX)],
            "rot": [0, 0, 0], "scale": [FX, FX, FX], "dummy": [0, 0]}


def bdhc_bytes():
    x0, z0, x1, z1 = IL.BDHC_RECT
    to_l = lambda t: (t * 16 - 256) * FX   # noqa: E731
    y = 16 + 16 * IL.FLOOR_H
    plate = (to_l(x0), to_l(z0), to_l(x1), to_l(z1), (0, FX, 0), int(round(-y * FX)))
    return mapdata.write_bdhc(mapdata.build_bdhc([plate]))


def face_keys(model):
    out = {}
    for mi, si in nsbmd.shape_material_pairs(model):
        m = model["materials"][mi]
        tris, quads = nsbmd.prims_to_faces(nsbmd.dl_primitives(nsbmd.dl_decode(model["shapes"][si]["dl"])))
        out.setdefault(m["name"], []).extend(tuple((v["pos"], v["uv"], v["color"]) for v in f) for f in tris + quads)
    return {k: sorted(v) for k, v in out.items()}


def check(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""))
    return ok


# ------------------------------------------------------------------------------------------------ registrations
def add_after_last(path, last, new, quoted=True):
    """Appends `new` after the entry `last` in a meson list or an order file (keeps its line endings)."""
    s = open(path, newline="").read()
    if (f"'{new}'" if quoted else new) in s.split():
        return False
    if quoted:
        a = f"'{last}'"
        i = s.index(a)
        eol = "\r\n" if s[i + len(a):].startswith(",\r\n") or s[i + len(a):].startswith("\r\n") else "\n"
        indent = s[s.rindex("\n", 0, i) + 1:i]
        assert s[i + len(a):].lstrip(" ").startswith(eol), f"{last} is not the last entry of {path}"
        s = s[:i + len(a)] + "," + eol + indent + f"'{new}'" + s[i + len(a):]
    else:
        lines = s.splitlines(keepends=True)
        assert lines[-1].strip() == last, f"{last} is not the last line of {path}"
        eol = lines[-1][len(lines[-1].rstrip("\r\n")):] or "\n"
        lines[-1] = lines[-1].rstrip("\r\n") + eol
        lines.append(new + eol)
        s = "".join(lines)
    open(path, "w", newline="").write(s)
    return True


def register():
    done = []
    if add_after_last(os.path.join(MAPS, "meson.build"), f"map_data_{MAP_ID - 1:03d}.bin", f"map_data_{MAP_ID:03d}.bin"):
        done.append("map_data meson.build")
    if add_after_last(os.path.join(MAPS, "map_data.order"), f"map_data_{MAP_ID - 1:03d}.bin",
                      f"map_data_{MAP_ID:03d}.bin", quoted=False):
        done.append("map_data.order")
    s = open(MAPS_TXT, newline="").read()
    if f"MAP_{MAP_ID}\n" not in s:
        assert f"MAP_{MAP_ID - 1}\nMAP_NONE" in s
        open(MAPS_TXT, "w", newline="").write(s.replace(f"MAP_{MAP_ID - 1}\nMAP_NONE",
                                                        f"MAP_{MAP_ID - 1}\nMAP_{MAP_ID}\nMAP_NONE"))
        done.append("maps.txt")
    if add_after_last(os.path.join(MATRICES, "meson.build"), f"map_matrix_{MATRIX_ID - 1:03d}.json",
                      f"map_matrix_{MATRIX_ID:03d}.json"):
        done.append("matrices meson.build")
    if add_after_last(os.path.join(MATRICES, "map_matrices.order"), f"map_matrix_{MATRIX_ID - 1:03d}.bin",
                      f"map_matrix_{MATRIX_ID:03d}.bin", quoted=False):
        done.append("map_matrices.order")
    if add_after_last(os.path.join(TEXSETS, "meson.build"), f"map_texture_set_{SET_ID - 1:03d}.nsbtx",
                      f"map_texture_set_{SET_ID:03d}.nsbtx"):
        done.append("texture_sets meson.build")
    if add_after_last(os.path.join(TEXSETS, "map_texture_set.order"), f"map_texture_set_{SET_ID - 1:03d}.nsbtx",
                      f"map_texture_set_{SET_ID:03d}.nsbtx", quoted=False):
        done.append("map_texture_set.order")
    return done


def write_area():
    import narc
    header, btnf, files = narc.read_files(AREA_DATA)
    entry = struct.pack("<4H", PROPS_LIST, SET_ID, 0, AREA_LIGHT)
    assert len(files) >= AREA_ID, f"area_data has {len(files)} entries; entry {AREA_ID} would leave a gap"
    if len(files) > AREA_ID:
        old = struct.unpack("<4H", files[AREA_ID])
        assert old[1] == SET_ID, f"area data entry 0x{AREA_ID:X} already exists and uses set {old[1]}"
        files[AREA_ID] = entry
    else:
        files.append(entry)
    narc.write_files(AREA_DATA, header, btnf, files)


# ------------------------------------------------------------------------------------------------ main
def main():
    args = sys.argv[1:]
    write = "--write" in args
    preview = args[args.index("--preview") + 1] if "--preview" in args else None
    ok = True

    mesh = json.load(open(ASSET))
    used = sorted({m["texture"] for m in mesh["materials"]})
    set_bytes, textures = build_texset(used)
    model = nsbmd.mesh_to_model(mesh, (0, 0), name=MODEL_NAME, textures=textures)
    nsb = nsbmd.build_bmd([model])
    perm = mapdata.write_permissions(IL.grid())
    props = mapdata.write_props([exit_mat_prop()])
    bd = bdhc_bytes()
    data = mapdata.pack(perm, props, nsb, bd)

    # ---- round trips
    back = nsbmd.parse_bmd(nsb)["models"][0]
    ok &= check("NSBMD build -> parse -> build identical", nsbmd.build_bmd([back]) == nsb)
    ok &= check("NSBMD decoded faces equal the built faces", face_keys(back) == face_keys(model))
    n_mesh = sum(len(me["tris"]) + len(me["quads"]) for me in mesh["meshes"])
    st = nsbmd.model_stats(back)
    ok &= check("NSBMD polygon count equals the mesh.json face count", st["polygons"] == n_mesh,
                f"{st['polygons']} ({st['triangles']} tris, {st['quads']} quads), mesh {n_mesh}")
    s = nsbtx.parse(set_bytes)
    ok &= check("NSBTX parse -> build identical",
                nsbtx.build(s["textures"], s["palettes"], keep_offsets=True, pal_flag=s["header"]["pal_flag"]) == set_bytes)
    pals = {p["name"]: p["colors"] for p in s["palettes"]}
    bad = []
    for t in s["textures"]:
        px, _ = nsbtx.decode(t, pals.get(textures[t["name"]]["palette"]))
        src = png.read(os.path.join(TEXDIR, t["name"] + ".png")).pixels
        same = all((a[3] < 128) == (b[3] < 128) and (a[3] < 128 or all(abs(a[i] - (b[i] >> 3 << 3)) <= 8
                                                                        for i in range(3)))
                   for ra, rb in zip(px, src) for a, b in zip(ra, rb))
        if not same:
            bad.append(t["name"])
    ok &= check("NSBTX textures decode to their PNGs (5-bit colour, 1-bit alpha tolerance)", not bad,
                f"{len(s['textures'])} textures, mismatches {bad}")
    missing = sorted({m["texture"] for m in back["materials"]} - {t["name"] for t in s["textures"]})
    ok &= check("every material's texture is in set 075", not missing, str(missing) if missing else "")
    sec = mapdata.unpack(data)
    ok &= check("map_data unpack -> pack identical",
                mapdata.pack(sec["permissions"], sec["props"], sec["model"], sec["bdhc"]) == data)

    # ---- collision and heights
    g = mapdata.read_permissions(sec["permissions"])
    ok &= check("permissions equal interior_layout", g == IL.grid())
    b = mapdata.read_bdhc(sec["bdhc"])
    bad_h = []
    for z in range(32):
        for x in range(32):
            want = IL.height(x, z)
            cx, cz = mapdata.tile_centre(x, z)
            got = mapdata.height_at(b, cx, cz)
            wy = None if want is None else int(round((16 + 16 * want) * FX))
            if got != wy and (want is not None or got is not None):
                bad_h.append((x, z, want, got))
    ok &= check("BDHC height at every tile centre equals interior_layout (and is defined on every walkable tile)",
                not bad_h and all(IL.height(x, z) is not None for z in range(32) for x in range(32)
                                  if not IL.collision(x, z) & IL.BLOCK), f"{len(bad_h)} off {bad_h[:5]}")
    ok &= check("arrival tile of the stair warp has a height", IL.height(*IL.STAIR_ARRIVAL) is not None,
                f"{IL.STAIR_ARRIVAL}")
    ex = IL.collision(*IL.EXIT_TILE)
    sw = IL.collision(*IL.STAIR_TILE)
    ok &= check("exit mat tile 0x65 walkable, stair warp tile 0x5E blocked by the barricade",
                ex == IL.EXIT_MAT and sw == IL.STAIRS_EAST | IL.BLOCK, f"exit 0x{ex:04X}, stair 0x{sw:04X}")
    evs = json.load(open(os.path.join(ROOT, "res", "field", "events", "events_verity_castle_1f.json")))
    got_w = [((w["x"], w["z"]), w["dest_header_id"], w["dest_warp_id"]) for w in evs["warp_events"]]
    ok &= check("events_verity_castle_1f.json warps match interior_layout.WARPS", got_w == list(IL.WARPS), str(got_w))
    # props: the exit mat must be in props list 21 (else the field does not load it)
    sys.path.insert(0, os.path.join(HERE, "..", "coronet_lava"))
    import narc
    ab = narc.read_files(AREA_BUILD)[2][PROPS_LIST]
    n = struct.unpack_from("<H", ab)[0]
    lst = struct.unpack_from(f"<{n}H", ab, 2)
    ok &= check(f"exit mat build model {IL.EXIT_MAT_MODEL} is in props list {PROPS_LIST}", IL.EXIT_MAT_MODEL in lst,
                str(list(lst)))

    # ---- budgets
    texel, pal_b = nsbtx.vram_usage(s)
    stats = [{"chunk": MAP_ID, "polygons": st["polygons"], "model_bytes": len(nsb), "bdhc_bytes": len(bd)}]
    errors, warnings = assemble.check_budgets(stats, vram=texel + pal_b)
    print(f"model {len(nsb)} B (buffer {assemble.MODEL_BUFFER}), {st['polygons']} polygons "
          f"(whole room; the camera sees at most all of them, per-frame limit 2048), {st['vertices_sent']} vertices, "
          f"{len(model['materials'])} materials; BDHC {len(bd)} B; map_data {len(data)} B")
    print(f"texture set 075: {', '.join(t['name'] for t in s['textures'])}; VRAM {texel} texel + {pal_b} palette = "
          f"{texel + pal_b} B (largest stock set {assemble.VRAM_PROVEN})")
    for w in warnings:
        print("warning: " + w)
    ok &= check("budgets", not errors, "; ".join(errors))

    if preview:
        os.makedirs(preview, exist_ok=True)
        json.dump(nsbmd.model_to_mesh(back, (0, 0), name="interior_1f"),
                  open(os.path.join(preview, "interior_1f.mesh.json"), "w"))
        bm = narc.read_files(BUILD_MODEL)[2]
        p = exit_mat_prop()
        pb = nsbmd.parse_bmd(bm[p["model"]])
        pm = pb["models"][0]
        pmesh = nsbmd.model_to_mesh(pm, (0, 0), name="exit_mat", offset=[v / FX for v in p["pos"]])
        json.dump(pmesh, open(os.path.join(preview, "exit_mat.mesh.json"), "w"))
        if pb["tex0"]:
            import dump_stock
            os.makedirs(os.path.join(preview, "textures"), exist_ok=True)
            dump_stock.export_textures(pb["tex0"], os.path.join(preview, "textures"),
                                       {x["texture"]: x["palette"] for x in pm["materials"]})
        print(f"preview meshes in {preview}")

    if not ok:
        raise SystemExit("checks failed")
    if write:
        open(os.path.join(MAPS, f"map_data_{MAP_ID:03d}.bin"), "wb").write(data)
        open(os.path.join(TEXSETS, f"map_texture_set_{SET_ID:03d}.nsbtx"), "wb").write(set_bytes)
        mx = {"name": MATRIX_NAME, "headers": [], "altitudes": [], "maps": [[f"MAP_{MAP_ID}"]]}
        with open(os.path.join(MATRICES, f"map_matrix_{MATRIX_ID:03d}.json"), "w", newline="\n") as fh:
            fh.write(json.dumps(mx, indent=4) + "\n")
        write_area()
        print("wrote map_data_666.bin, map_texture_set_075.nsbtx, map_matrix_289.json, area data entry 0x4C")
        print("registered: " + (", ".join(register()) or "already registered"))
    else:
        print("dry run (use --write to write the files)")


if __name__ == "__main__":
    main()
