#!/usr/bin/env python3
"""SCRATCH ONLY, never commit the result: place the Arc 2 sprites on Twinleaf Town for an in-game check.

    python3 tools/arc2_sprites/scratch_events.py A     # or B; edits res/field/events/events_twinleaf_town.json
    make release
    (run ingame_capture.py, see docs/story/art/arc2/README.md)
    git checkout res/field/events/events_twinleaf_town.json

The player stands at (116,886) facing up, so the visible tiles are about x 109-123, z 882-892.
Scene A: Indra and Kahn in every facing (rows z 887 / 889: down, up, left, right) next to the stock
Cynthia and Sailor they were built from, one wandering copy of each.
Scene B: both Looker disguises in every facing next to the stock Looker, the three idle objects next to
Arc 1's rift and the stock Galactic grunt, one wandering copy of each Looker.
Scene T: Indra and the two Eclipse grunts as real trainers (TRAINER_INDRA_DEPOT, _ECLIPSE_GRUNT_ARC2_01/02) at
z 891 looking north up x 112 / 116 / 120, for battle_capture.py (the trainer battle sprites).
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "res/field/events/events_twinleaf_town.json"
LOOKS = [("MOVEMENT_TYPE_LOOK_SOUTH", 1), ("MOVEMENT_TYPE_LOOK_NORTH", 0),
         ("MOVEMENT_TYPE_LOOK_WEST", 2), ("MOVEMENT_TYPE_LOOK_EAST", 3)]


def obj(i, gfx, movement, x, z, direction=1, rx=0, rz=0):
    return {"id": f"LOCALID_ART_SCRATCH_{i}", "graphics_id": gfx, "movement_type": movement,
            "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "0", "script": 0, "initial_dir": direction,
            "data": [], "movement_range_x": rx, "movement_range_z": rz, "x": x, "y": 1, "z": z}


def facings(out, gfx, z):
    for k, (movement, d) in enumerate(LOOKS):
        out.append(obj(len(out), gfx, movement, 109 + 2 * k, z, d))


def scene(name):
    o = []
    if name == "A":
        facings(o, "OBJ_EVENT_GFX_INDRA", 887)
        facings(o, "OBJ_EVENT_GFX_KAHN", 889)
        o.append(obj(len(o), "OBJ_EVENT_GFX_CYNTHIA", "MOVEMENT_TYPE_LOOK_SOUTH", 118, 887))
        o.append(obj(len(o), "OBJ_EVENT_GFX_SAILOR", "MOVEMENT_TYPE_LOOK_SOUTH", 118, 889))
        o.append(obj(len(o), "OBJ_EVENT_GFX_INDRA", "MOVEMENT_TYPE_WANDER_AROUND", 111, 884, 1, 1, 0))
        o.append(obj(len(o), "OBJ_EVENT_GFX_KAHN", "MOVEMENT_TYPE_WANDER_AROUND", 120, 885, 1, 0, 1))
    elif name == "T":
        # trainers for the battle-sprite check: each looks north up its own column
        for i, (gfx, script, x) in enumerate((("OBJ_EVENT_GFX_INDRA", "TRAINER_INDRA_DEPOT", 112),
                                               ("OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", "TRAINER_ECLIPSE_GRUNT_ARC2_01", 116),
                                               ("OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", "TRAINER_ECLIPSE_GRUNT_ARC2_02", 120))):
            t = obj(i, gfx, "MOVEMENT_TYPE_LOOK_NORTH", x, 891, 0)
            t.update({"trainer_type": "TRAINER_TYPE_NORMAL", "script": script, "data": [4]})
            o.append(t)
    else:
        facings(o, "OBJ_EVENT_GFX_LOOKER_JANITOR", 887)
        facings(o, "OBJ_EVENT_GFX_LOOKER_NEWSPAPER", 889)
        o.append(obj(len(o), "OBJ_EVENT_GFX_LOOKER", "MOVEMENT_TYPE_LOOK_SOUTH", 118, 887))
        o.append(obj(len(o), "OBJ_EVENT_GFX_GRUNT_M", "MOVEMENT_TYPE_LOOK_SOUTH", 118, 889))
        o.append(obj(len(o), "OBJ_EVENT_GFX_ECLIPSE_CRATE", "MOVEMENT_TYPE_NONE", 120, 887))
        o.append(obj(len(o), "OBJ_EVENT_GFX_SHARD_FRAME", "MOVEMENT_TYPE_NONE", 120, 889))
        o.append(obj(len(o), "OBJ_EVENT_GFX_RIFT_ARC2", "MOVEMENT_TYPE_NONE", 112, 884))
        o.append(obj(len(o), "OBJ_EVENT_GFX_ARC1_RIFT", "MOVEMENT_TYPE_NONE", 110, 884))
        o.append(obj(len(o), "OBJ_EVENT_GFX_LOOKER_JANITOR", "MOVEMENT_TYPE_WANDER_AROUND", 120, 885, 1, 0, 0))
        o.append(obj(len(o), "OBJ_EVENT_GFX_LOOKER_NEWSPAPER", "MOVEMENT_TYPE_WANDER_AROUND", 122, 887, 1, 0, 1))
    return o


def main():
    name = (sys.argv[1] if len(sys.argv) > 1 else "A").upper()
    data = json.loads(EVENTS.read_text())
    data["object_events"] = [o for o in data["object_events"] if not o["id"].startswith("LOCALID_ART_SCRATCH_")]
    objects = scene(name)
    data["object_events"] += objects
    EVENTS.write_text(json.dumps(data, indent=4) + "\n")
    print(f"{EVENTS.name}: scene {name}, +{len(objects)} scratch objects")


if __name__ == "__main__":
    main()
