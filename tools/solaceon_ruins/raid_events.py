#!/usr/bin/env python3
"""Writes the raid's object, bg and coord events into the Ruins maps of the macOS tree
(res/field/maps/solaceon_ruins_*/events.json), from the one object table in placements.py (raid_maps.md section 4).
Standard library only.

    python3 tools/solaceon_ruins/raid_events.py           # dry run: prints what would change
    python3 tools/solaceon_ruins/raid_events.py --write

What it translates from placements.py (whose snippets are in the old main-branch schema):
- ids: SOL_RUINS_<X> -> LOCALID_<X> (the mac tree's local-id names; headless `talk` resolves them per map);
- the map-local flags: FLAG_UNK_0x0030/31/32 -> FLAG_MAP_LOCAL_HIDE_OBSTACLE_16/17/18 (the depot's precedent);
- TODO_* script ids -> the labels in each room's scripts.s (SCRIPTS below). Rooms 2-6 have no raid scripts of
  their own: their crates, frames and crystals have no script (nothing happens when talked to, stock precedent);
- trainers -> {"trainer": {"id", "sight_range"}} (no script; the engine runs the trainer script);
- initial_dir 0-3 -> DIR_*.
Raid objects are appended after the stock ones (stock local ids keep their numbers). Re-running replaces the raid
objects in place (matched by id), so the result is the same every time.

Also: Room 1's coord-free scene (init frame table, not an event), Room 7's switch bg event and its two coord
triggers, the Room 2 Hiker's hidden flag (hidden during the raid) and Room 7's HM05 ball renamed to TM30.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import placements as P  # noqa: E402

MAPS = os.path.join(ROOT, "res", "field", "maps")
LOCAL = {"FLAG_UNK_0x0030": "FLAG_MAP_LOCAL_HIDE_OBSTACLE_16",
         "FLAG_UNK_0x0031": "FLAG_MAP_LOCAL_HIDE_OBSTACLE_17",
         "FLAG_UNK_0x0032": "FLAG_MAP_LOCAL_HIDE_OBSTACLE_18"}
DIRNAME = {"N": "DIR_NORTH", "S": "DIR_SOUTH", "W": "DIR_WEST", "E": "DIR_EAST"}

# TODO_* (placements.py) -> label, per room. Missing = no script.
SCRIPTS = {
    "ROOM_1": {"TODO_RopeSign": "SolaceonRuinsRoom1_RaidRope", "TODO_CyrusRoom1": "SolaceonRuinsRoom1_RaidCyrus"},
    "ROOM_2_NORTHEAST_DEAD_END": {"TODO_GeneratorA": "SolaceonRuinsRoom2NortheastDeadEnd_Generator"},
    "ROOM_4_SOUTHEAST_DEAD_END": {"TODO_GeneratorB": "SolaceonRuinsRoom4SoutheastDeadEnd_Generator"},
    "ROOM_6_NORTHWEST_DEAD_END": {"TODO_GeneratorC": "SolaceonRuinsRoom6NorthwestDeadEnd_Generator"},
    "ROOM_7": {"TODO_Barrier": "SolaceonRuinsRoom7_RaidBarrier", "TODO_CyrusBarrier": "SolaceonRuinsRoom7_RaidCyrus",
               "TODO_LookerVault": "SolaceonRuinsRoom7_RaidLooker", "TODO_Rubble": "SolaceonRuinsRoom7_RaidRubble",
               "TODO_Rack": None},    # lit/dark racks: per object below
}
RACK_LIT, RACK_DARK = "SolaceonRuinsRoom7_RaidRackLit", "SolaceonRuinsRoom7_RaidRackDark"

BG_EVENTS = {
    "ROOM_7": [collections.OrderedDict([("script", "SolaceonRuinsRoom7_RaidSwitch"), ("type", "BG_EVENT_TYPE_FACING"),
                                        ("x", 5), ("z", 11), ("y", 0), ("player_facing_dir", "BG_EVENT_DIR_SOUTH")])],
}
COORDS = {
    # walking up to the barrier at 30-32 (VAR_MAP_LOCAL_0x02 = 1 from OnTransition, once per visit)
    "ROOM_7": [
        collections.OrderedDict([("script", "SolaceonRuinsRoom7_RaidBarrierStep"), ("x", 2), ("z", 4), ("y", 0), ("width", 7),
                                 ("length", 1), ("var", "VAR_MAP_LOCAL_0x02"), ("value", 1)]),
        # the first step past the barrier line at 33 (or 40, after losing to Indra): the vault scene
        collections.OrderedDict([("script", "SolaceonRuinsRoom7_RaidVault"), ("x", 2), ("z", 6), ("y", 0), ("width", 7),
                                 ("length", 1), ("var", "VAR_MAP_LOCAL_0x01"), ("value", 1)]),
    ],
}


def map_dir(room):
    return os.path.join(MAPS, "solaceon_ruins_" + room.lower().replace("room_5_southeast_dead_end",
                                                                          "room_5_southeast_deadend"))


def localid(o):
    return "LOCALID_" + o["id"][len("SOL_RUINS_"):]


def mac_event(room, o):
    d = collections.OrderedDict()
    d["id"] = localid(o)
    d["graphics_id"] = o["gfx"]
    j = P.event_json(o)
    d["movement_type"] = j["movement_type"]
    d["trainer_type"] = j["trainer_type"]
    d["hidden_flag"] = LOCAL.get(o["flag"], o["flag"])
    if o["trainer"]:
        d["trainer"] = collections.OrderedDict([("id", o["trainer"]), ("sight_range", o["sight"])])
    else:
        label = SCRIPTS.get(room, {}).get(o["script"])
        if o["script"] == "TODO_Rack":
            label = RACK_DARK if o["gfx"].endswith("_DARK") else RACK_LIT
        if label:
            d["script"] = label
    d["initial_dir"] = DIRNAME[o["dir"]]
    if not o["trainer"]:
        d["data"] = []
    d["movement_range_x"] = 0
    d["movement_range_z"] = 0
    d["x"], d["z"], d["y"] = o["x"], o["z"], 0
    return d


def merge(lst, new, key):
    """Replaces entries of lst with the same key, appends the rest; returns the number changed."""
    idx = {e.get(key) if isinstance(key, str) else key(e): i for i, e in enumerate(lst)}
    changed = 0
    for e in new:
        k = e.get(key) if isinstance(key, str) else key(e)
        if k in idx:
            if lst[idx[k]] != e:
                lst[idx[k]] = e
                changed += 1
        else:
            lst.append(e)
            changed += 1
    return changed


def stock_fixes(room, ev):
    n = 0
    if room == "ROOM_2":
        for o in ev["object_events"]:
            if o["id"] == "LOCALID_HIKER" and o["hidden_flag"] != "FLAG_MAP_LOCAL_HIDE_OBSTACLE_16":
                o["hidden_flag"] = "FLAG_MAP_LOCAL_HIDE_OBSTACLE_16"     # hidden 20-49 by OnTransition
                n += 1
    if room == "ROOM_7":
        for o in ev["object_events"]:
            if o["id"] == "LOCALID_ITEM_HM05":
                o["id"] = "LOCALID_ITEM_TM30"
                o["hidden_flag"] = "FLAG_OBTAINED_SOLACEON_RUINS_ROOM_7_TM30"
                o["script"] = "VisibleItems_SolaceonRuinsRoom7_TM30"
                n += 1
    return n


def main():
    write = "--write" in sys.argv
    total = 0
    for room, objs in P.ROOMS.items():
        path = os.path.join(map_dir(room), "events.json")
        ev = json.load(open(path), object_pairs_hook=collections.OrderedDict)
        n = stock_fixes(room, ev)
        n += merge(ev["object_events"], [mac_event(room, o) for o in objs], "id")
        n += merge(ev["bg_events"], BG_EVENTS.get(room, []), lambda e: (e["x"], e["z"], e["script"]))
        n += merge(ev["coord_events"], COORDS.get(room, []), "script")
        if room == "ROOM_2" and not objs:
            pass
        total += n
        text = json.dumps(ev, indent=4) + "\n"
        if text != open(path).read():
            print(("wrote " if write else "would write ") + os.path.relpath(path, ROOT) + f" ({n} change(s))")
            if write:
                with open(path, "w") as f:
                    f.write(text)
    # Room 2's stock Hiker fix (Room 2 has raid objects too, so it is handled above)
    print(f"{total} change(s)")


if __name__ == "__main__":
    main()
