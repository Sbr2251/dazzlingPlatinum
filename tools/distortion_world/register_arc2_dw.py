#!/usr/bin/env python3
"""Register the five Arc 2 Distortion World maps (R0 stubs). Idempotent; standard library only.

Each map is a standalone DW floor (like MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS): its own header, matrix, two
map_data blocks (copies of the arc1 seams blocks 667/668), scripts + init scripts, events, text bank, location name,
tw_arc record and wall-grid attr members (four reserved per map, the first a copy of the arc1 seams grid), and an
entry in src/overlay009/ov9_02249960.c (map count, connection list, object list, step hook).

The owners (rift-a: ravaged_path, eterna_forest; rift-b: route_214, route_213, lost_tower) replace only their own
files: tools/distortion_world/<name>.json (tw_arc spec), map_data_<a>/<b>.bin, map_matrix_<n>.json, the scripts,
events and text, and their own blocks in ov9 (sArc2Dw<Name>Objects, Arc2Dw<Name>_HandleStep).

Usage: python3 tools/distortion_world/register_arc2_dw.py
"""
import json
import os
import re
import shutil
import struct
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "coronet_lava"))
import narc  # noqa: E402

ENTRY_X, ENTRY_Z = 20, 12   # arc1 seams entry platform (facing west)
EXIT_X, EXIT_Z = 17, 12     # stub exit: three steps west of the entry, on the same platform row

# name, Camel, matrix id, map_data pair, first attr id, overworld exit (header, x, z, dir), progress on calm, owner
MAPS = [
    ("ravaged_path", "RavagedPath", 291, (669, 670), 13, ("MAP_HEADER_RAVAGED_PATH", 19, 46, "DIR_SOUTH"), 15, "rift-a"),
    ("eterna_forest", "EternaForest", 292, (671, 672), 17, ("MAP_HEADER_ETERNA_FOREST", 84, 37, "DIR_SOUTH"), 26, "rift-a"),
    ("route_214", "Route214", 293, (673, 674), 21, ("MAP_HEADER_ROUTE_214", 726, 665, "DIR_SOUTH"), 63, "rift-b"),
    ("route_213", "Route213", 294, (675, 676), 25, ("MAP_HEADER_ROUTE_213", 715, 831, "DIR_SOUTH"), 84, "rift-b"),
    ("lost_tower", "LostTower", 295, (677, 678), 29, ("MAP_HEADER_ROUTE_209_LOST_TOWER_2F", 5, 8, "DIR_WEST"), 95, "rift-b"),
]
ATTRS_PER_MAP = 4
TEXT_KEYS = {"ravaged_path": 40211, "eterna_forest": 40213, "route_214": 40217, "route_213": 40219,
             "lost_tower": 40223, "arc2_common": 40229}


def path(*p):
    return os.path.join(ROOT, *p)


def read(p):
    with open(path(p)) as f:
        return f.read()


def write(p, text):
    with open(path(p), "w") as f:
        f.write(text)


def insert_lines_before(p, marker, new_lines):
    lines = read(p).split("\n")
    missing = [l for l in new_lines if l not in lines]
    if not missing:
        return
    i = lines.index(marker)
    lines[i:i] = missing
    write(p, "\n".join(lines))


def append_lines(p, new_lines):
    text = read(p)
    lines = text.rstrip("\n").split("\n")
    missing = [l for l in new_lines if l not in lines]
    if missing:
        write(p, "\n".join(lines + missing) + "\n")


def meson_files_append(p, list_open, after_entry, entries):
    """Insert quoted entries after `after_entry` (a quoted file name) inside a files( ... ) list."""
    text = read(p)
    missing = [e for e in entries if f"'{e}'" not in text]
    if not missing:
        return
    start = text.index(list_open)
    at = text.index(f"'{after_entry}'", start)
    line_end = text.index("\n", at)
    line = text[at:line_end]
    if line.endswith(","):
        ins = "".join(f"\n    '{e}'," for e in missing)
        text = text[:line_end] + ins + text[line_end:]
    else:  # last entry without a trailing comma
        ins = ",".join(f"\n    '{e}'" for e in missing)
        text = text[:line_end] + "," + ins + text[line_end:]
    write(p, text)


def header_block(name, camel, matrix):
    up = name.upper()
    return f"""    // Arc 2 rift (R0 stub, see docs/arc2/rift_contract.md): standalone DW floor, fields copied from
    // DISTORTION_WORLD_ARC1_SEAMS. Matrix {matrix}, tw_arc spec tools/distortion_world/{name}.json.
    [MAP_HEADER_DW_{up}] = {{
        .areaDataArchiveID = 0x4A,
        .unk_01 = 0xF,
        .mapMatrixID = {matrix},
        .scriptsArchiveID = scripts_dw_{name},
        .initScriptsArchiveID = scripts_init_dw_{name},
        .msgArchiveID = TEXT_BANK_DW_{up},
        .dayMusicID = SEQ_PL_D_GIRATINA,
        .nightMusicID = SEQ_PL_D_GIRATINA,
        .wildEncountersArchiveID = ENCOUNTERS_NONE,
        .eventsArchiveID = events_dw_{name},
        .mapLabelTextID = LocationNames_Text_DW{camel},
        .mapLabelWindowID = 0x4,
        .weather = OVERWORLD_WEATHER_CLEAR,
        .cameraType = CAMERA_TYPE_INTERIOR_ORTHOGRAPHIC,
        .mapType = 0x3,
        .battleBG = BACKGROUND_DISTORTION_WORLD,
        .isBikeAllowed = FALSE,
        .isRunningAllowed = FALSE,
        .isEscapeRopeAllowed = FALSE,
        .isFlyAllowed = FALSE,
    }},
"""


def script_text(name, camel, exit_, progress, owner):
    hdr, x, z, d = exit_
    return f"""#include "macros/scrcmd.inc"
#include "res/text/bank/dw_{name}.h"

// Arc 2 rift: MAP_HEADER_DW_{name.upper()} (R0 stub; owner {owner}). docs/arc2/rift_contract.md is the contract:
//   entry   overworld script warps here: Warp MAP_HEADER_DW_{name.upper()}, 0, {ENTRY_X}, {ENTRY_Z}, DIR_WEST
//   exit    Warp {hdr}, 0, {x}, {z}, {d}
//   calm    totem calmed sets VAR_ARC2_PROGRESS = {progress}
// The stub has no puzzle: the coord event at ({EXIT_X},{EXIT_Z}) (three steps west of the entry) runs the exit.

    ScriptEntry DW{camel}_OnTransition
    ScriptEntry DW{camel}_Exit
    ScriptEntryEnd

DW{camel}_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

DW{camel}_Exit:
    LockAll
    Message DW{camel}_Text_StubExit
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp {hdr}, 0, {x}, {z}, {d}
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End
"""


INIT_SCRIPT = """#include "macros/scrcmd.inc"


    InitScriptEntry_OnTransition 1
    InitScriptEntryEnd

    InitScriptEnd
"""


def events_text():
    return json.dumps({
        "bg_events": [],
        "object_events": [],
        "warp_events": [],
        "coord_events": [
            {"script": 2, "x": EXIT_X, "z": EXIT_Z, "y": 0, "width": 1, "length": 1,
             "var": "VAR_MAP_LOCAL_0", "value": 0},
        ],
    }, indent=4) + "\n"


def text_bank(name, camel):
    return json.dumps({
        "key": TEXT_KEYS[name],
        "messages": [
            {"id": f"DW{camel}_Text_StubExit", "en_US": ["The rift pulls you back out.\n", "(Stub: this floor isn't built yet.)"]},
        ],
    }, indent=2, ensure_ascii=False) + "\n"


ARC2_COMMON = {
    "key": TEXT_KEYS["arc2_common"],
    "messages": [
        {"id": "Arc2Common_Text_LedgerWhoKnew", "en_US": ["Who could have told Team Eclipse?"]},
        {"id": "Arc2Common_Text_LedgerCyrus", "en_US": "Cyrus"},
        {"id": "Arc2Common_Text_LedgerGarius", "en_US": "Garius"},
        {"id": "Arc2Common_Text_LedgerRuth", "en_US": "Ruth"},
        {"id": "Arc2Common_Text_LedgerBadLuck", "en_US": "Bad luck"},
        {"id": "Arc2Common_Text_ResonatorMissing", "en_US": ["Nothing answers.\n", "Something seems to be missing."]},
        {"id": "Arc2Common_Text_ResonatorSurge", "en_US": ["{STRVAR_1 1, 0, 0}'s energy surges\n", "through the Resonator!"]},
    ],
}


def tw_spec(name, attr0):
    rows = json.load(open(path("tools/distortion_world/arc1_seams.json")))["platforms"][0]["rows"]
    return {
        "map": f"MAP_HEADER_DW_{name.upper()}",
        "clone_from": "MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS",
        "offset": [0, 0, 0],
        "attr_ids": list(range(attr0, attr0 + ATTRS_PER_MAP)),
        "platforms": [{"attr": attr0, "rows": rows}],
    }


OV9 = "src/overlay009/ov9_02249960.c"


def update_ov9():
    text = read(OV9)
    if "MAP_HEADER_DW_RAVAGED_PATH" in text:
        return
    text = text.replace(
        "// 11: the Arc 1 wall-walk puzzle map (MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS), standalone like the Giratina room.\n"
        "#define DISTORTION_WORLD_MAP_COUNT 11\n",
        "// 11: the Arc 1 wall-walk puzzle map (MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS), standalone like the Giratina room.\n"
        "// 12-16: the five Arc 2 rifts (MAP_HEADER_DW_*), standalone (docs/arc2/rift_contract.md).\n"
        "#define DISTORTION_WORLD_MAP_COUNT 16\n")
    conn = "".join(f"""    {{
        .prevID = MAP_HEADER_INVALID,
        .currID = MAP_HEADER_DW_{m[0].upper()},
        .nextID = MAP_HEADER_INVALID
    }},
""" for m in MAPS).rstrip(",\n") + "\n"
    old = """        .currID = MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS,
        .nextID = MAP_HEADER_INVALID
    }
};"""
    assert old in text
    text = text.replace(old, """        .currID = MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS,
        .nextID = MAP_HEADER_INVALID
    },
""" + conn + "};")
    # Step hooks: one stub per map, each owned by that map's rift workstream.
    hooks = "\n// Arc 2 rifts (R0 stubs): per-map step hooks, called from ov9_0224A71C with DW world tile coordinates. Each\n" \
            "// rift workstream fills in only its own function (rift-a: RavagedPath, EternaForest; rift-b: the rest).\n"
    for m in MAPS:
        hooks += f"""static BOOL Arc2Dw{m[1]}_HandleStep(DistWorldSystem *system, int x, int y, int z)
{{
    return FALSE;
}}

"""
    anchor = "BOOL ov9_0224A71C(FieldSystem *fieldSystem)\n"
    assert anchor in text
    text = text.replace(anchor, hooks + anchor, 1)
    old = """            } else if (v6 == MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS) {
                if (Arc1Seams_HandleStep(v5, v1, v2, v3) == TRUE) {
                    return 1;
                }
            }"""
    assert old in text
    new = old[:-len("            }")]
    for m in MAPS:
        new += f"""            }} else if (v6 == MAP_HEADER_DW_{m[0].upper()}) {{
                if (Arc2Dw{m[1]}_HandleStep(v5, v1, v2, v3) == TRUE) {{
                    return 1;
                }}
"""
    new += "            }"
    text = text.replace(old, new)
    # Object lists (DW overlay objects, local IDs 0x80+), empty until the owner fills them.
    old = "static const UnkStruct_ov9_02252EB4 Unk_ov9_02252EB4[] = {"
    assert old in text
    lists = "// Arc 2 rifts (R0 stubs): DW overlay objects per map (local IDs 0x80+), each owned by that map's rift workstream.\n"
    for m in MAPS:
        lists += f"static const UnkStruct_ov9_0224EF30 *sArc2Dw{m[1]}Objects[] = {{\n    NULL\n}};\n\n"
    text = text.replace(old, lists + old)
    old = "    { MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS, sArc1SeamsObjects },\n"
    assert old in text
    text = text.replace(old, old + "".join(f"    {{ MAP_HEADER_DW_{m[0].upper()}, sArc2Dw{m[1]}Objects }},\n" for m in MAPS))
    write(OV9, text)


def update_tw_arc():
    attr_path = path("res/prebuilt/fielddata/tornworld/tw_arc_attr.narc")
    for m in MAPS:
        name, attr0 = m[0], m[4]
        spec_path = f"tools/distortion_world/{name}.json"
        if not os.path.exists(path(spec_path)):
            write(spec_path, json.dumps(tw_spec(name, attr0), indent=4) + "\n")
        subprocess.check_call([sys.executable, path("tools/distortion_world/twarc.py"), "build", path(spec_path)])
        # reserve the map's spare attr members (all blocked) so the owners never append past another map's ids
        hdr, btnf, attr = narc.read_files(attr_path)
        changed = False
        for aid in range(attr0 + 1, attr0 + ATTRS_PER_MAP):
            if aid >= len(attr):
                assert aid == len(attr)
                attr.append(struct.pack("<1024H", *([0x8000] * 1024)))
                changed = True
        if changed:
            narc.write_files(attr_path, hdr, btnf, attr)


def main():
    # 1. header enum, header table, location names
    insert_lines_before("generated/map_headers.txt", "MAP_HEADER_COUNT", [f"MAP_HEADER_DW_{m[0].upper()}" for m in MAPS])
    h = read("include/data/map_headers.h")
    if "MAP_HEADER_DW_RAVAGED_PATH" not in h:
        i = h.rindex("};")
        h = h[:i] + "".join(header_block(m[0], m[1], m[2]) for m in MAPS) + h[i:]
        write("include/data/map_headers.h", h)
    ln = json.load(open(path("res/text/location_names.json")))
    ids = {x["id"] for x in ln["messages"]}
    for m in MAPS:
        if f"LocationNames_Text_DW{m[1]}" not in ids:
            ln["messages"].append({"id": f"LocationNames_Text_DW{m[1]}", "en_US": "Distortion World"})
    write("res/text/location_names.json", json.dumps(ln, indent=2, ensure_ascii=False) + "\n")

    # 2. map data blocks and matrices
    insert_lines_before("generated/maps.txt", "MAP_NONE = 65535", [f"MAP_{n}" for m in MAPS for n in m[3]])
    for m in MAPS:
        for src, dst in zip((667, 668), m[3]):
            d = path(f"res/field/maps/data/map_data_{dst}.bin")
            if not os.path.exists(d):
                shutil.copyfile(path(f"res/field/maps/data/map_data_{src}.bin"), d)
        mp = f"res/field/maps/matrices/map_matrix_{m[2]}.json"
        if not os.path.exists(path(mp)):
            write(mp, json.dumps({"name": f"m_dwa2_{m[2] - 290}", "headers": [], "altitudes": [],
                                  "maps": [[f"MAP_{m[3][0]}", f"MAP_{m[3][1]}"]]}, indent=4) + "\n")
    append_lines("res/field/maps/data/map_data.order", [f"map_data_{n}.bin" for m in MAPS for n in m[3]])
    meson_files_append("res/field/maps/data/meson.build", "map_data_files", "map_data_668.bin",
                       [f"map_data_{n}.bin" for m in MAPS for n in m[3]])
    append_lines("res/field/maps/matrices/map_matrices.order", [f"map_matrix_{m[2]}.bin" for m in MAPS])
    meson_files_append("res/field/maps/matrices/meson.build", "matrix_data_srcs", "map_matrix_290.json",
                       [f"map_matrix_{m[2]}.json" for m in MAPS])

    # 3. text banks
    append_lines("generated/text_banks.txt", [f"TEXT_BANK_DW_{m[0].upper()}" for m in MAPS] + ["TEXT_BANK_ARC2_COMMON"])
    for m in MAPS:
        if not os.path.exists(path(f"res/text/dw_{m[0]}.json")):
            write(f"res/text/dw_{m[0]}.json", text_bank(m[0], m[1]))
    if not os.path.exists(path("res/text/arc2_common.json")):
        write("res/text/arc2_common.json", json.dumps(ARC2_COMMON, indent=2, ensure_ascii=False) + "\n")

    # 4. scripts and events
    for m in MAPS:
        name, camel = m[0], m[1]
        if not os.path.exists(path(f"res/field/scripts/scripts_dw_{name}.s")):
            write(f"res/field/scripts/scripts_dw_{name}.s", script_text(name, camel, m[5], m[6], m[7]))
            write(f"res/field/scripts/scripts_init_dw_{name}.s", INIT_SCRIPT)
        if not os.path.exists(path(f"res/field/events/events_dw_{name}.json")):
            write(f"res/field/events/events_dw_{name}.json", events_text())
    scr = [s for m in MAPS for s in (f"scripts_dw_{m[0]}", f"scripts_init_dw_{m[0]}")]
    append_lines("res/field/scripts/scripts.order", scr)
    meson_files_append("res/field/scripts/meson.build", "scr_seq_files", "scripts_init_oreburgh_mine_side_tunnel.s",
                       [s + ".s" for s in scr])
    append_lines("res/field/events/zone_event.order", [f"events_dw_{m[0]}" for m in MAPS])
    meson_files_append("res/field/events/meson.build", "events_files", "events_oreburgh_mine_side_tunnel.json",
                       [f"events_dw_{m[0]}.json" for m in MAPS])

    # 5. tw_arc records + attr grids, overlay 9
    update_tw_arc()
    update_ov9()
    print("Arc 2 DW maps registered:", ", ".join(f"MAP_HEADER_DW_{m[0].upper()}" for m in MAPS))


if __name__ == "__main__":
    main()
