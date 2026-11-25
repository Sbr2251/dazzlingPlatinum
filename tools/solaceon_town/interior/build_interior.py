#!/usr/bin/env python3
"""Builds the Sanctuary hall interior map (MAP_HEADER_SOLACEON_SANCTUARY) and registers it in the macOS-port tree
(branch solaceon-mac: pret's per-map folders, res/field/mapmodels/, res/field/area_data/). Standard library only.

Usage: python3 tools/solaceon_town/interior/build_interior.py [--write] [--preview <dir>]
       (dry run by default: builds everything in memory and runs every check)

Inputs:
  tools/solaceon_town/interior/assets/sanctuary.mesh.json + assets/textures/   (art/sanctuary_interior.py)
  tools/solaceon_town/interior/layout.py                                      (collision, heights, warps)
  stock files from git at BASE_REV (only for the "stock entries unchanged" checks)

Outputs (--write; every path is a constant below):
  res/field/mapmodels/data/map_data_680.bin              permissions + exit-mat prop + NSBMD + BDHC
  res/field/mapmodels/texture_sets/map_texture_set_076.nsbtx
  res/field/area_data/area_data_078.json                 prop_model_set_021 (stock minimal indoor list: 078 exit
                                                         mat, 152), map_texture_set_076, lighting_set_001 (indoor)
  res/field/maps/groups.json                             map group 296 "SolaceonSanctuary" = [["MAP_680"]]
  res/field/maps/solaceon_sanctuary/header.json          created if missing (registration fields checked otherwise)
  stubs, created only if missing (the town-scripts workstream owns them afterwards):
    res/field/maps/solaceon_sanctuary/events.json (the exit warp only), scripts.s (one placeholder script),
    res/text/solaceon_sanctuary.json (one placeholder message). No init.s: like Verity Castle 1F, an interior needs
    none (mapproc then points the header at the empty init script); add one plus its scripts.order line when needed.
  registrations (append only): mapmodels/data meson.build + map_data.order + generated/maps.txt,
    mapmodels/texture_sets meson.build + map_texture_sets.order, area_data meson.build + area_data.order,
    groups.json, generated/map_headers.txt, res/field/scripts.order, generated/text_banks.txt.
  Idempotent: --write runs the write twice and fails if the second pass changes a byte.

Checks (all must pass, else --write is refused): NSBMD/NSBTX/map_data round trips; textures decode to their PNGs;
permissions == layout.grid(); BDHC height at every tile == layout.height() (arrival tile included); the exit warp in
events.json == layout.WARPS (destination warp names resolved through the destination map's events.json); budgets
(model buffer, polygons, VRAM within stock precedent); every shared registry keeps all of its BASE_REV content (only
appended entries), every new id sits at its index in its order file, and the new files did not exist at BASE_REV.
"""
import difflib
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
LV = os.path.join(ROOT, "tools", "lake_verity")
sys.path.insert(0, LV)
sys.path.insert(0, os.path.join(ROOT, "tools", "coronet_lava"))

import assemble  # noqa: E402  (tools/lake_verity; imports its own layout.py)
import mapdata  # noqa: E402
import nsbmd  # noqa: E402
import nsbtx  # noqa: E402
import png  # noqa: E402

_spec = importlib.util.spec_from_file_location("sanctuary_layout", os.path.join(HERE, "layout.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

# ------------------------------------------------------------------------------------------------ ids and paths
# solaceon-mac when this branch was cut: the stock/registry baseline for the append-only checks.
BASE_REV = "49269afc8"

MAP_ID = 680                  # map_data_680.bin / MAP_680 (679 was the last used)
SET_ID = 76                   # map_texture_set_076 (075 = Verity Castle 1F)
AREA_ID = 78                  # area_data_078 (= 0x4E; 077 was the last used)
GROUP_INDEX = 296             # index of the new map group in groups.json (295 = DW_LostTower)
GROUP_ID = "SolaceonSanctuary"
GROUP_NAME = "m_sol_sanct"    # matrix name, at most 15 characters like stock
PROP_SET = 21                 # prop_model_set_021: [078 exit mat, 152] (Verity Castle 1F's area 076 uses it too)
LIGHTING_SET = 1              # lighting_set_001, the indoor light (Hearthome's Foreign Building uses it)
HEADER = "MAP_HEADER_SOLACEON_SANCTUARY"
NAME = "solaceon_sanctuary"   # the map folder and the text bank file (pret: lower-case header name)
TEXT_BANK = "TEXT_BANK_SOLACEON_SANCTUARY"
TEXT_KEY = 40231
MODEL_NAME = "sol_sanctuary"
EXIT_WARP_ID = "WARP_SOLACEON_TOWN"   # the Sanctuary's warp 0 (the name Solaceon Town's door uses as dest_warp_id)
FX = 4096

MAPMODEL_DATA_REL = "res/field/mapmodels/data"
TEXSETS_REL = "res/field/mapmodels/texture_sets"
AREA_REL = "res/field/area_data"
GROUPS_REL = "res/field/maps/groups.json"
MAPS_REL = "res/field/maps"
MAPDIR_REL = f"{MAPS_REL}/{NAME}"
TEXT_REL = f"res/text/{NAME}.json"
SCRIPTS_ORDER_REL = "res/field/scripts.order"
PROP_SET_REL = f"res/field/props/model_sets/prop_model_set_{PROP_SET:03d}.json"
PROP_MODELS_REL = "res/field/props/models"
LIGHTING_REL = f"res/field/lighting/lighting_set_{LIGHTING_SET:03d}.json"

MAP_DATA_FILE = f"map_data_{MAP_ID:03d}.bin"
SET_FILE = f"map_texture_set_{SET_ID:03d}.nsbtx"
AREA_FILE = f"area_data_{AREA_ID:03d}.json"

ASSET = os.path.join(HERE, "assets", "sanctuary.mesh.json")
TEXDIR = os.path.join(HERE, "assets", "textures")


def P(rel):
    return os.path.join(ROOT, rel)


# Interior orthographic camera, indoor battle background, no bike/run/Escape Rope/Fly; Solaceon's location name,
# popup window and town theme, as the other Solaceon interiors (the News Press, whose door this map takes over).
HEADER_JSON = {
    "areaData": f"area_data_{AREA_ID:03d}",
    "mapGroup": GROUP_ID,
    "locationName": "LocationNames_Text_SolaceonTown",
    "textBank": TEXT_BANK,
    "popupStyle": "MAP_LABEL_WINDOW_TOWN",
    "weather": "OVERWORLD_WEATHER_CLEAR",
    "cameraType": "CAMERA_TYPE_INTERIOR_ORTHOGRAPHIC",
    "battleBackground": "BACKGROUND_INDOORS_1",
    "mapType": "MAP_TYPE_INDOORS",
    "preloaded": 15,
    "musicDay": "SEQ_CITY06_D_sseq",
    "musicNight": "SEQ_CITY06_N_sseq",
    "isBikeAllowed": False,
    "isRunningAllowed": False,
    "isEscapeRopeAllowed": False,
    "isFlyAllowed": False,
}
HEADER_KEYS_FIXED = ("areaData", "mapGroup", "textBank")   # the registration; other fields are the owner's to tune

AREA_JSON = {
    "mapPropSet": f"prop_model_set_{PROP_SET:03d}",
    "mapTextureSet": f"map_texture_set_{SET_ID:03d}",
    "lightingSet": f"lighting_set_{LIGHTING_SET:03d}",
    "dummy": 0,
}

GROUP_JSON = {"id": GROUP_ID, "name": GROUP_NAME, "headers": [], "altitudes": [], "maps": [[f"MAP_{MAP_ID}"]]}

SCRIPT_STUB = """#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_sanctuary.h"

// MAP_HEADER_SOLACEON_SANCTUARY, the Sanctuary hall (stub from tools/solaceon_town/interior/build_interior.py).
// The town-scripts workstream owns this file. Tiles, NPC spots, sign tiles and the office doorway are in
// tools/solaceon_town/interior/layout.py and docs/solaceon_redesign/interior.md.

    ScriptEntry SolaceonSanctuary_Placeholder
    ScriptEntryEnd

SolaceonSanctuary_Placeholder:
    ShowScrollingSign SolaceonSanctuary_Text_Placeholder
    End
"""

TEXT_STUB = {"key": TEXT_KEY, "messages": [
    {"id": "SolaceonSanctuary_Text_Placeholder", "en_US": ["The Sanctuary is quiet."]}]}


def map_warps(header):
    """The warp_events of the map whose header is `header` (pret folder = lower-case header name)."""
    stem = header[len("MAP_HEADER_"):].lower()
    p = P(f"{MAPS_REL}/{stem}/events.json")
    return json.load(open(p))["warp_events"] if os.path.exists(p) else None


def dest_warp_name(header, index):
    warps = map_warps(header)
    return warps[index]["id"] if warps and index < len(warps) else None


def events_stub():
    warps = []
    for i, (t, h, w) in enumerate(L.WARPS):
        warps.append({"id": EXIT_WARP_ID if i == 0 else f"WARP_{NAME.upper()}_{i}", "x": t[0], "z": t[1],
                      "dest_header_id": h, "dest_warp_id": dest_warp_name(h, w)})
    return {"bg_events": [], "object_events": [], "warp_events": warps, "coord_events": []}


def json_text(obj, indent):
    return json.dumps(obj, indent=indent) + "\n"


# ------------------------------------------------------------------------------------------------ model pieces
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
    x, z = L.EXIT_TILE
    return {"model": L.EXIT_MAT_MODEL, "pos": [int((x + 0.5 - 16) * 16 * FX), 0, int((z + 0.5 - 16) * 16 * FX)],
            "rot": [0, 0, 0], "scale": [FX, FX, FX], "dummy": [0, 0]}


def bdhc_bytes():
    x0, z0, x1, z1 = L.BDHC_RECT
    to_l = lambda t: (t * 16 - 256) * FX   # noqa: E731
    y = 16 + 16 * L.FLOOR_H
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


def git_show(rel):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{BASE_REV}:{rel}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


# ------------------------------------------------------------------------------------------------ registrations
def _read(path):
    with open(path, newline="") as f:
        return f.read()


def _write(path, s):
    with open(path, "w", newline="") as f:
        f.write(s)


def meson_append(path, after, new):
    """Inserts the quoted entry `new` right after the quoted entry `after` in a meson files() list."""
    s = _read(path)
    if f"'{new}'" in s:
        return False
    a = f"'{after}'"
    i = s.index(a) + len(a)
    line_start = s.rindex("\n", 0, i - len(a)) + 1
    indent = s[line_start:i - len(a)]
    if s[i:i + 1] == ",":
        j = s.index("\n", i)
        s = s[:j] + "\n" + indent + f"'{new}'," + s[j:]
    else:
        s = s[:i] + ",\n" + indent + f"'{new}'" + s[i:]
    _write(path, s)
    return True


def line_append(path, new, before=None):
    """Appends a line (or inserts it before the line `before`) once."""
    s = _read(path)
    lines = s.split("\n")
    if new in lines:
        return False
    if before is None:
        s = s.rstrip("\n") + "\n" + new + "\n"
    else:
        k = lines.index(before)
        lines[k:k] = [new]
        s = "\n".join(lines)
    _write(path, s)
    return True


def group_append(path):
    """Appends the map group to groups.json in its own formatting (2-space indent, one row per line)."""
    s = _read(path)
    groups = json.loads(s)
    if any(g["id"] == GROUP_ID for g in groups):
        return False
    rows = ",\n".join("      [" + ", ".join(json.dumps(m) for m in row) + "]" for row in GROUP_JSON["maps"])
    block = ("  {\n"
             f'    "id": {json.dumps(GROUP_ID)},\n'
             f'    "name": {json.dumps(GROUP_NAME)},\n'
             '    "headers": [],\n'
             '    "altitudes": [],\n'
             '    "maps": [\n' + rows + "\n    ]\n"
             "  }")
    k = s.rstrip().rindex("]")
    head = s[:k].rstrip()
    assert head.endswith("}"), "groups.json: unexpected end"
    _write(path, head + ",\n" + block + "\n" + s[k:])
    return True


REG = [  # (relative path, kind, args): every shared registry this builder touches
    (f"{MAPMODEL_DATA_REL}/meson.build", "meson", (f"map_data_{MAP_ID - 1:03d}.bin", MAP_DATA_FILE)),
    (f"{MAPMODEL_DATA_REL}/map_data.order", "line", (MAP_DATA_FILE, None)),
    ("generated/maps.txt", "line", (f"MAP_{MAP_ID}", "MAP_NONE = 65535")),
    (f"{TEXSETS_REL}/meson.build", "meson", (f"map_texture_set_{SET_ID - 1:03d}.nsbtx", SET_FILE)),
    (f"{TEXSETS_REL}/map_texture_sets.order", "line", (f"map_texture_set_{SET_ID:03d}", None)),
    (f"{AREA_REL}/meson.build", "meson", (f"area_data_{AREA_ID - 1:03d}.json", AREA_FILE)),
    (f"{AREA_REL}/area_data.order", "line", (f"area_data_{AREA_ID:03d}", None)),
    ("generated/map_headers.txt", "line", (HEADER, "MAP_HEADER_COUNT")),
    (SCRIPTS_ORDER_REL, "line", (f"scripts_{NAME}", None)),
    ("generated/text_banks.txt", "line", (TEXT_BANK, None)),
    (GROUPS_REL, "group", ()),
]

# where each new id must sit: (relative path, entry, index)
INDEXED = [
    (f"{MAPMODEL_DATA_REL}/map_data.order", MAP_DATA_FILE, MAP_ID),
    ("generated/maps.txt", f"MAP_{MAP_ID}", MAP_ID),
    (f"{TEXSETS_REL}/map_texture_sets.order", f"map_texture_set_{SET_ID:03d}", SET_ID),
    (f"{AREA_REL}/area_data.order", f"area_data_{AREA_ID:03d}", AREA_ID),
]


def register():
    done = []
    for rel, kind, args in REG:
        p = P(rel)
        if kind == "meson":
            ch = meson_append(p, *args)
        elif kind == "line":
            ch = line_append(p, *args)
        else:
            ch = group_append(p)
        if ch:
            done.append(rel)
    return done


def ours(line):
    keys = (f"map_data_{MAP_ID:03d}", f"MAP_{MAP_ID}", f"map_texture_set_{SET_ID:03d}", f"area_data_{AREA_ID:03d}",
            "SOLACEON_SANCTUARY", NAME)
    return any(k in line for k in keys)


def registry_check():
    """Every shared registry keeps all of its BASE_REV lines, in order; lines we add are ours (other workstreams'
    later appends are reported, not failed). A meson entry that gained a trailing comma counts as kept. groups.json
    is compared as JSON: the BASE_REV groups must be an unchanged prefix."""
    problems, foreign = [], []
    for rel in sorted({r[0] for r in REG}):
        base = git_show(rel)
        if base is None:
            problems.append(f"{rel}: not in {BASE_REV}")
            continue
        if rel == GROUPS_REL:
            old, new = json.loads(base), json.loads(_read(P(rel)))
            if new[:len(old)] != old:
                problems.append(f"{rel}: stock groups changed")
            foreign += [f"{rel}: group {g['id']}" for g in new[len(old):] if g["id"] != GROUP_ID]
            continue
        old = base.decode().split("\n")
        new = _read(P(rel)).split("\n")
        sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            removed, added = old[i1:i2], new[j1:j2]
            # tolerate "'x'" -> "'x'," (the previous last entry of a meson list gains a comma)
            if removed and added and all(a.rstrip(",") == r.rstrip(",") for r, a in zip(removed, added[:len(removed)])):
                added = added[len(removed):]
                removed = []
            if removed:
                problems.append(f"{rel}: stock lines changed/removed: {removed[:3]}")
            foreign += [f"{rel}: {a.strip()}" for a in added if a.strip() and not ours(a)]
    return problems, foreign


def index_check():
    """Each new id is at its index (dry run: it would be appended at exactly that index)."""
    bad = []
    for rel, entry, idx in INDEXED:
        lines = [x for x in _read(P(rel)).split("\n") if x.strip()]
        if entry in lines:
            if lines.index(entry) != idx:
                bad.append(f"{rel}: {entry} at {lines.index(entry)}, want {idx}")
        else:
            n = len(lines) - (1 if rel == "generated/maps.txt" else 0)   # MAP_NONE stays last
            if n != idx:
                bad.append(f"{rel}: {entry} would land at {n}, want {idx}")
    groups = json.loads(_read(P(GROUPS_REL)))
    ids = [g["id"] for g in groups]
    gi = ids.index(GROUP_ID) if GROUP_ID in ids else len(ids)
    if gi != GROUP_INDEX:
        bad.append(f"{GROUPS_REL}: group {GROUP_ID} at {gi}, want {GROUP_INDEX}")
    elif GROUP_ID in ids and groups[gi] != GROUP_JSON:
        bad.append(f"{GROUPS_REL}: group {GROUP_ID} differs from {GROUP_JSON}")
    return bad


def write_files(data, set_bytes):
    """Writes everything; returns the list of files whose bytes changed."""
    changed = []

    def put(rel, payload, only_if_missing=False):
        p = P(rel)
        if only_if_missing and os.path.exists(p):
            return
        b = payload.encode() if isinstance(payload, str) else payload
        if os.path.exists(p) and open(p, "rb").read() == b:
            return
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(b)
        changed.append(rel)

    put(f"{MAPMODEL_DATA_REL}/{MAP_DATA_FILE}", data)
    put(f"{TEXSETS_REL}/{SET_FILE}", set_bytes)
    put(f"{AREA_REL}/{AREA_FILE}", json_text(AREA_JSON, 4))
    put(f"{MAPDIR_REL}/header.json", json_text(HEADER_JSON, 2), only_if_missing=True)
    put(f"{MAPDIR_REL}/events.json", json_text(events_stub(), 4), only_if_missing=True)
    put(f"{MAPDIR_REL}/scripts.s", SCRIPT_STUB, only_if_missing=True)
    put(TEXT_REL, json_text(TEXT_STUB, 2), only_if_missing=True)
    changed += register()
    return changed


def tree_hash(rels):
    out = {}
    for rel in rels:
        p = P(rel)
        out[rel] = hashlib.sha1(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
    return out


WRITTEN = [f"{MAPMODEL_DATA_REL}/{MAP_DATA_FILE}", f"{TEXSETS_REL}/{SET_FILE}", f"{AREA_REL}/{AREA_FILE}",
           f"{MAPDIR_REL}/header.json", f"{MAPDIR_REL}/events.json", f"{MAPDIR_REL}/scripts.s", TEXT_REL] + \
          sorted({r[0] for r in REG})


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
    perm = mapdata.write_permissions(L.grid())
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
    ok &= check("every texture is 16-colour (pltt16)", all(t["fmt"] == 3 for t in s["textures"]))
    missing = sorted({m["texture"] for m in back["materials"]} - {t["name"] for t in s["textures"]})
    ok &= check(f"every material's texture is in set {SET_ID:03d}", not missing, str(missing) if missing else "")
    sec = mapdata.unpack(data)
    ok &= check("map_data unpack -> pack identical",
                mapdata.pack(sec["permissions"], sec["props"], sec["model"], sec["bdhc"]) == data)

    # ---- collision, heights, warps
    g = mapdata.read_permissions(sec["permissions"])
    ok &= check("permissions equal layout.grid()", g == L.grid())
    b = mapdata.read_bdhc(sec["bdhc"])
    bad_h = []
    for z in range(32):
        for x in range(32):
            want = L.height(x, z)
            cx, cz = mapdata.tile_centre(x, z)
            got = mapdata.height_at(b, cx, cz)
            wy = None if want is None else int(round((16 + 16 * want) * FX))
            if got != wy:
                bad_h.append((x, z, want, got))
    walk = [(x, z) for z in range(32) for x in range(32) if not L.collision(x, z) & L.BLOCK]
    ok &= check("BDHC height at every tile centre equals layout.height(), defined on every walkable tile",
                not bad_h and all(L.height(x, z) is not None for x, z in walk),
                f"{len(walk)} walkable tiles, {len(bad_h)} off {bad_h[:5]}")
    ax, az = L.ARRIVAL_TILE
    ok &= check("arrival tile (exit mat) has the floor height and is the 0x65 exit mat",
                L.height(ax, az) == L.FLOOR_H and L.collision(ax, az) == L.EXIT_MAT, f"{L.ARRIVAL_TILE}")
    ok &= check("office doorway tile is walkable floor (an object event there blocks the office)",
                L.collision(*L.DOORWAY) == L.FLOOR, f"{L.DOORWAY}")
    for name, (x, z, _) in L.NPC_SPOTS.items():
        if L.collision(x, z) & L.BLOCK:
            ok &= check(f"NPC spot {name} walkable", False, f"({x},{z})")
    ok &= check("NPC spots are walkable", True, f"{len(L.NPC_SPOTS)} spots")
    sign_bad = [(n, t) for n, (tiles, rd, _) in L.SIGNS.items() for t in tiles if not L.collision(*t) & L.BLOCK]
    read_bad = [(n, rd) for n, (tiles, rd, _) in L.SIGNS.items() if L.collision(*rd) & L.BLOCK]
    ok &= check("sign tiles are blocked and their reading tiles walkable", not sign_bad and not read_bad,
                f"{sign_bad} {read_bad}" if sign_bad or read_bad else f"{len(L.SIGNS)} signs")

    evp = P(f"{MAPDIR_REL}/events.json")
    evs = json.load(open(evp)) if os.path.exists(evp) else events_stub()
    got_w = []
    for w in evs["warp_events"]:
        dest = map_warps(w["dest_header_id"]) or []
        idx = next((i for i, d in enumerate(dest) if d.get("id") == w["dest_warp_id"]), w["dest_warp_id"])
        got_w.append(((w["x"], w["z"]), w["dest_header_id"], idx))
    ok &= check("events.json warps equal layout.WARPS (dest warp names resolved to indices)"
                + ("" if os.path.exists(evp) else " (stub to write)"), got_w == list(L.WARPS), str(got_w))
    ok &= check(f"warp 0 is named {EXIT_WARP_ID}", evs["warp_events"][0].get("id") == EXIT_WARP_ID,
                str(evs["warp_events"][0].get("id")))
    town = map_warps(L.WARPS[0][1])
    tw = town[L.WARPS[0][2]]
    door = tw["dest_header_id"] == HEADER and tw["dest_warp_id"] == EXIT_WARP_ID
    print(f"note: {L.WARPS[0][1]} warp {L.WARPS[0][2]} ({tw['id']} at {tw['x']},{tw['z']}) -> "
          f"{tw['dest_header_id']} / {tw['dest_warp_id']}" + ("" if door else "  (not pointed at the Sanctuary yet)"))

    props_list = json.load(open(P(PROP_SET_REL)))["mapPropModels"]
    want_prop = f"prop_model_{L.EXIT_MAT_MODEL:03d}_nsbmd"
    ok &= check(f"exit mat prop model {L.EXIT_MAT_MODEL} is in prop_model_set_{PROP_SET:03d}", want_prop in props_list,
                str(props_list))
    ok &= check(f"lighting_set_{LIGHTING_SET:03d} exists", os.path.exists(P(LIGHTING_REL)))
    hp = P(f"{MAPDIR_REL}/header.json")
    if os.path.exists(hp):
        h = json.load(open(hp))
        ok &= check("header.json registration fields match", all(h.get(k) == HEADER_JSON[k] for k in HEADER_KEYS_FIXED),
                    str({k: h.get(k) for k in HEADER_KEYS_FIXED}))
        diff = {k: h.get(k) for k in HEADER_JSON if h.get(k) != HEADER_JSON[k] and k not in HEADER_KEYS_FIXED}
        if diff:
            print(f"note: header.json differs from the builder's defaults (kept): {diff}")

    # ---- budgets
    texel, pal_b = nsbtx.vram_usage(s)
    stats = [{"chunk": MAP_ID, "polygons": st["polygons"], "model_bytes": len(nsb), "bdhc_bytes": len(bd)}]
    errors, warnings = assemble.check_budgets(stats, vram=texel + pal_b)
    if st["polygons"] > assemble.WINDOW_POLYS:
        errors.append(f"{st['polygons']} polygons (the whole room can be on screen) > {assemble.WINDOW_POLYS}")
    print(f"model {len(nsb)} B (buffer {assemble.MODEL_BUFFER}), {st['polygons']} polygons (whole room; the "
          f"camera sees at most all of them, limit {assemble.WINDOW_POLYS} of 2048), {st['vertices_sent']} vertices, "
          f"{len(model['materials'])} materials; BDHC {len(bd)} B; map_data {len(data)} B")
    print(f"texture set {SET_ID:03d}: {len(s['textures'])} textures ({', '.join(t['name'] for t in s['textures'])}); "
          f"VRAM {texel} texel + {pal_b} palette = {texel + pal_b} B (largest stock set {assemble.VRAM_PROVEN})")
    for w in warnings:
        print("warning: " + w)
    ok &= check("budgets", not errors, "; ".join(errors))

    # ---- shared registries: stock content unchanged (only appends), ids at their indices, new files new
    problems, foreign = registry_check()
    ok &= check(f"shared registries keep all their {BASE_REV} content (append only)", not problems,
                "; ".join(problems[:4]))
    for f in foreign[:10]:
        print(f"note: entry not from this builder (another workstream?): {f}")
    bad_idx = index_check()
    ok &= check(f"new ids sit at their indices (map_data {MAP_ID}, set {SET_ID:03d}, area {AREA_ID:03d}, "
                f"group {GROUP_INDEX})", not bad_idx, "; ".join(bad_idx))
    for rel in (f"{MAPMODEL_DATA_REL}/{MAP_DATA_FILE}", f"{TEXSETS_REL}/{SET_FILE}", f"{AREA_REL}/{AREA_FILE}",
                f"{MAPDIR_REL}/header.json", TEXT_REL):
        ok &= check(f"{rel} is new (not in {BASE_REV})", git_show(rel) is None)
    for rel in (f"{MAPMODEL_DATA_REL}/map_data_{MAP_ID - 1:03d}.bin",
                f"{TEXSETS_REL}/map_texture_set_{SET_ID - 1:03d}.nsbtx",
                f"{AREA_REL}/area_data_{AREA_ID - 1:03d}.json"):
        ok &= check(f"{os.path.basename(rel)} (the previous id) is in {BASE_REV}", git_show(rel) is not None)
    ok &= check("ASCII only in the header, stub events, script and text",
                all(c < 128 for c in (json.dumps(HEADER_JSON) + json.dumps(events_stub()) + SCRIPT_STUB
                                      + json.dumps(TEXT_STUB)).encode()))

    if preview:
        os.makedirs(preview, exist_ok=True)
        json.dump(nsbmd.model_to_mesh(back, (0, 0), name="sanctuary"),
                  open(os.path.join(preview, "sanctuary.mesh.json"), "w"))
        p = exit_mat_prop()
        pb = nsbmd.parse_bmd(open(P(f"{PROP_MODELS_REL}/prop_model_{p['model']:03d}.nsbmd"), "rb").read())
        pm = pb["models"][0]
        json.dump(nsbmd.model_to_mesh(pm, (0, 0), name="exit_mat", offset=[v / FX for v in p["pos"]]),
                  open(os.path.join(preview, "exit_mat.mesh.json"), "w"))
        if pb["tex0"]:
            import dump_stock
            os.makedirs(os.path.join(preview, "textures"), exist_ok=True)
            dump_stock.export_textures(pb["tex0"], os.path.join(preview, "textures"),
                                       {x["texture"]: x["palette"] for x in pm["materials"]})
        print(f"preview meshes in {preview}")

    if not ok:
        raise SystemExit("checks failed; nothing written")
    if not write:
        print("dry run (use --write to write the files)")
        return
    changed = write_files(data, set_bytes)
    print("written: " + (", ".join(changed) or "nothing (already up to date)"))
    before = tree_hash(WRITTEN)
    again = write_files(data, set_bytes)
    after = tree_hash(WRITTEN)
    if again or before != after:
        raise SystemExit(f"second --write pass changed files: {again or [k for k in before if before[k] != after[k]]}")
    print(f"idempotent: a second write pass changed none of the {len(WRITTEN)} files")
    problems, _ = registry_check()
    bad_idx = index_check()
    if problems or bad_idx:
        raise SystemExit("registry check failed after writing: " + "; ".join(problems + bad_idx))
    print("registry checks pass after writing")


if __name__ == "__main__":
    main()
