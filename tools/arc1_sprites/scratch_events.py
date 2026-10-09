#!/usr/bin/env python3
"""SCRATCH ONLY, never commit the result: place the Arc 1 sprites on three maps for an in-game check.

    python3 tools/arc1_sprites/scratch_events.py            # edit the three events JSON files
    flock .build.lock make release
    (run ingame_capture.py, see README)
    git checkout res/field/events/events_twinleaf_town.json \
        res/field/events/events_oreburgh_mine_b2f.json res/field/events/events_jubilife_city.json

Twinleaf: every facing of the three walkers in rows, the two idle objects next to stock Grunt M and
the stock totem, and one wandering copy of each walker. Oreburgh Mine B2F: the scene 14 staging (rift
(9,15), violet Hitmonlee (9,14), Garius (9,16)). Jubilife TV plaza: Saros and four grunts with Garius,
Cyrus and Looker for contrast.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "res/field/events"


def obj(i, gfx, movement, x, z, direction=1, rx=0, rz=0):
    return {"id": f"LOCALID_ART_SCRATCH_{i}", "graphics_id": gfx, "movement_type": movement,
            "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "0", "script": 0, "initial_dir": direction,
            "data": [], "movement_range_x": rx, "movement_range_z": rz, "x": x, "y": 1, "z": z}


def add(name, objects):
    path = EVENTS / name
    data = json.loads(path.read_text())
    if any(o["id"].startswith("LOCALID_ART_SCRATCH_") for o in data["object_events"]):
        print(f"{name}: already placed")
        return
    data["object_events"] += objects
    path.write_text(json.dumps(data, indent=4) + "\n")
    print(f"{name}: +{len(objects)} scratch objects")


def main():
    looks = [("MOVEMENT_TYPE_LOOK_SOUTH", 1), ("MOVEMENT_TYPE_LOOK_NORTH", 0),
             ("MOVEMENT_TYPE_LOOK_WEST", 2), ("MOVEMENT_TYPE_LOOK_EAST", 3)]
    tw = []
    for gfx, z in (("OBJ_EVENT_GFX_SAROS", 888), ("OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", 890), ("OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", 892)):
        for k, (movement, d) in enumerate(looks):
            tw.append(obj(len(tw), gfx, movement, 110 + 2 * k, z, d))
    tw += [obj(len(tw), "OBJ_EVENT_GFX_ARC1_RIFT", "MOVEMENT_TYPE_NONE", 119, 888),
           obj(len(tw) + 1, "OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET", "MOVEMENT_TYPE_NONE", 121, 888),
           obj(len(tw) + 2, "OBJ_EVENT_GFX_GRUNT_M", "MOVEMENT_TYPE_LOOK_SOUTH", 119, 890),
           obj(len(tw) + 3, "OBJ_EVENT_GFX_TOTEM_HITMONLEE", "MOVEMENT_TYPE_NONE", 121, 890),
           obj(len(tw) + 4, "OBJ_EVENT_GFX_SAROS", "MOVEMENT_TYPE_WANDER_AROUND", 110, 883, 1, 1, 1),
           obj(len(tw) + 5, "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", "MOVEMENT_TYPE_WANDER_AROUND", 110, 886, 1, 1, 0),
           obj(len(tw) + 6, "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", "MOVEMENT_TYPE_WANDER_AROUND", 122, 885, 1, 1, 1)]
    add("events_twinleaf_town.json", tw)
    add("events_oreburgh_mine_b2f.json", [
        obj(0, "OBJ_EVENT_GFX_ARC1_RIFT", "MOVEMENT_TYPE_NONE", 9, 15),
        obj(1, "OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET", "MOVEMENT_TYPE_NONE", 9, 14),
        obj(2, "OBJ_EVENT_GFX_BARRY", "MOVEMENT_TYPE_LOOK_NORTH", 9, 16, 0),
        obj(3, "OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET", "MOVEMENT_TYPE_NONE", 13, 14),
        obj(4, "OBJ_EVENT_GFX_ARC1_RIFT", "MOVEMENT_TYPE_NONE", 15, 14)])
    add("events_jubilife_city.json", [
        obj(0, "OBJ_EVENT_GFX_SAROS", "MOVEMENT_TYPE_LOOK_SOUTH", 166, 752),
        obj(1, "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", "MOVEMENT_TYPE_LOOK_SOUTH", 162, 752),
        obj(2, "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", "MOVEMENT_TYPE_LOOK_SOUTH", 157, 753),
        obj(3, "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", "MOVEMENT_TYPE_LOOK_WEST", 168, 753, 2),
        obj(4, "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", "MOVEMENT_TYPE_LOOK_EAST", 159, 755, 3),
        obj(5, "OBJ_EVENT_GFX_CYRUS", "MOVEMENT_TYPE_LOOK_NORTH", 166, 756, 0),
        obj(6, "OBJ_EVENT_GFX_LOOKER", "MOVEMENT_TYPE_LOOK_NORTH", 161, 757, 0),
        obj(7, "OBJ_EVENT_GFX_BARRY", "MOVEMENT_TYPE_LOOK_NORTH", 164, 753, 0)])


if __name__ == "__main__":
    main()
