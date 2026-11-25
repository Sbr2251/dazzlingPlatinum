#!/usr/bin/env python3
"""The raid's object events in the Solaceon Ruins: one table, its checks, and the JSON snippets for raid-scripts.

Usage:
  python3 tools/solaceon_ruins/placements.py            checks (tiles, twins, sight lines, reachability per state)
  python3 tools/solaceon_ruins/placements.py --json     ready-to-paste object_events snippets, per room
  python3 tools/solaceon_ruins/placements.py --map      ASCII tile maps of every dressed room

Nothing here writes an events file (raid-scripts owns them). Script ids are "TODO_*" strings for raid-scripts to
replace; eye-contact trainers use the stock form ("script": "TRAINER_...", trainer_type TRAINER_TYPE_NORMAL,
data [sight]). Rooms are one chunk each, so x/z are the event coordinates.

Visibility (hidden_flag semantics: the object is hidden while the flag is set):
  persistent FLAG_SOL_RAID_A/B/C  generator A/B/C switched off (story)      -> hides that generator's "on" look
             FLAG_SOL_RAID_D      barrier dropped (story)                   -> hides the barrier
             FLAG_SOL_RAID_E      racks drained (story)                     -> hides the lit vault racks / core
             FLAG_SOL_RAID_F      NEW: raid over, set together with progress 50 -> hides crew and equipment
             FLAG_SOL_RAID_G      NEW: Indra gone, set when she enters the tunnel (45) -> hides Indra
  map-local FLAG_UNK_0x0030..32   cleared on every map load, set by the room's OnTransition script (Arc 2 depot
                                  precedent) for the "inverse" cases: off looks, dark racks, rubble, Looker, rope.
Rooms beyond Room 1 are unreachable before progress 20 (the rope in Room 1), so persistent flags that are still
clear before the raid never show anything to the player there.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ruins as R  # noqa: E402

sys.path.insert(0, os.path.join(R.ROOT, "tools", "world_art"))
import chunkedit as C  # noqa: E402
import mapdata  # noqa: E402

DIRS = {"N": 0, "S": 1, "W": 2, "E": 3}
LOOK = {"N": "MOVEMENT_TYPE_LOOK_NORTH", "S": "MOVEMENT_TYPE_LOOK_SOUTH", "W": "MOVEMENT_TYPE_LOOK_WEST",
        "E": "MOVEMENT_TYPE_LOOK_EAST"}
STEP = {"N": (0, -1), "S": (0, 1), "W": (-1, 0), "E": (1, 0)}

# new field sprites this design needs (specified in raid_maps.md, not registered): constant -> placeholder
NEW_SPRITES = {
    "OBJ_EVENT_GFX_SHARD_GENERATOR": "OBJ_EVENT_GFX_ECLIPSE_CRATE",
    "OBJ_EVENT_GFX_SHARD_GENERATOR_OFF": "OBJ_EVENT_GFX_ECLIPSE_CRATE",
    "OBJ_EVENT_GFX_SHARD_BARRIER": "OBJ_EVENT_GFX_RIFT_ARC2",
    "OBJ_EVENT_GFX_SHARD_FRAME_DARK": "OBJ_EVENT_GFX_SHARD_FRAME",
    "OBJ_EVENT_GFX_VIOLET_CRYSTAL_DARK": "OBJ_EVENT_GFX_VIOLET_CRYSTAL",
    "OBJ_EVENT_GFX_DIG_ROPE": "OBJ_EVENT_GFX_SIGNBOARD",
}


def O(id_, gfx, x, z, d="S", flag="0", script=None, trainer=None, sight=0, role="", blocks=True):
    return dict(id=id_, gfx=gfx, x=x, z=z, dir=d, flag=flag, script=script, trainer=trainer, sight=sight,
                role=role)


# --------------------------------------------------------------------------------------------------------------
# the table
# --------------------------------------------------------------------------------------------------------------

LOCAL_0 = "FLAG_UNK_0x0030"
LOCAL_1 = "FLAG_UNK_0x0031"
LOCAL_2 = "FLAG_UNK_0x0032"

ROOMS = collections.OrderedDict()

ROOMS["ROOM_1"] = [
    O("SOL_RUINS_R1_ROPE", "OBJ_EVENT_GFX_DIG_ROPE", 6, 3, "S", LOCAL_1, "TODO_RopeSign",
      role="rope on the stair down to Room 2, progress < 20 (sign: DIG SITE. STAFF ONLY.)"),
    O("SOL_RUINS_R1_GRUNT_01", "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", 6, 2, "S", LOCAL_0, trainer="TRAINER_ECLIPSE_GRUNT_SOL_01",
      sight=3, role="RAID_DIGGER: guards the stair to Room 2; sees (6,3)-(6,5)"),
    O("SOL_RUINS_R1_CYRUS", "OBJ_EVENT_GFX_CYRUS", 4, 7, "W", LOCAL_2, "TODO_CyrusRoom1",
      role="part 3: a hand on the west wall; only at progress 20 (the first entry), then walks deeper"),
    O("SOL_RUINS_R1_CRATE_0", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 4, 9, "S", LOCAL_0, "TODO_Crate",
      role="raid supplies by the scaffold"),
    O("SOL_RUINS_R1_CRATE_1", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 6, 7, "S", LOCAL_0, "TODO_Crate", role="raid supplies"),
]
ROOMS["ROOM_2"] = [
    O("SOL_RUINS_R2_CRATE_0", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 6, 6, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_R2_CRATE_1", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 6, 7, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_R2_FRAME_0", "OBJ_EVENT_GFX_SHARD_FRAME", 4, 8, "S", "FLAG_SOL_RAID_F", "TODO_Frame",
      role="an empty frame waiting to be wired (stays lit: it is not on a generator)"),
]
ROOMS["ROOM_2_NORTHEAST_DEAD_END"] = [
    O("SOL_RUINS_GEN_A_ON", "OBJ_EVENT_GFX_SHARD_GENERATOR", 7, 2, "S", "FLAG_SOL_RAID_A", "TODO_GeneratorA",
      role="generator A (on); talk from (7, 3) facing north"),
    O("SOL_RUINS_GEN_A_OFF", "OBJ_EVENT_GFX_SHARD_GENERATOR_OFF", 7, 2, "S", LOCAL_0, "TODO_GeneratorA",
      role="generator A (off look); same tile, complementary flag"),
    O("SOL_RUINS_GEN_A_RACK_ON", "OBJ_EVENT_GFX_SHARD_FRAME", 6, 2, "S", "FLAG_SOL_RAID_A", "TODO_GeneratorA",
      role="the rack it feeds (lit), beside it in the north row"),
    O("SOL_RUINS_GEN_A_RACK_OFF", "OBJ_EVENT_GFX_SHARD_FRAME_DARK", 6, 2, "S", LOCAL_0, "TODO_GeneratorA",
      role="the rack, dim"),
    O("SOL_RUINS_GEN_A_GUARD", "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", 5, 2, "S", "FLAG_SOL_RAID_F",
      trainer="TRAINER_ECLIPSE_GRUNT_SOL_02", sight=2, role="RAID_GEN_A_GUARD: sees (5, 3), (5, 4)"),
    O("SOL_RUINS_GEN_A_CRATE_0", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 4, 2, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_GEN_A_CRATE_1", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 4, 4, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
]
ROOMS["ROOM_3"] = [
    O("SOL_RUINS_R3_GRUNT_03", "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", 4, 8, "E", "FLAG_SOL_RAID_F",
      trainer="TRAINER_ECLIPSE_GRUNT_SOL_03", sight=2, role="RAID_TECH: watches row 8, (5,8),(6,8)"),
    O("SOL_RUINS_R3_CRATE_0", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 6, 5, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_R3_CRYSTAL_0", "OBJ_EVENT_GFX_VIOLET_CRYSTAL", 4, 4, "S", "FLAG_SOL_RAID_F", "TODO_Crystal",
      role="a shard cluster waiting to be racked"),
]
ROOMS["ROOM_4"] = [
    O("SOL_RUINS_R4_CRATE_0", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 6, 5, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_R4_CRATE_1", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 6, 6, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_R4_FRAME_0", "OBJ_EVENT_GFX_SHARD_FRAME", 6, 7, "S", "FLAG_SOL_RAID_F", "TODO_Frame"),
]
ROOMS["ROOM_4_SOUTHEAST_DEAD_END"] = [
    O("SOL_RUINS_GEN_B_ON", "OBJ_EVENT_GFX_SHARD_GENERATOR", 5, 2, "S", "FLAG_SOL_RAID_B", "TODO_GeneratorB",
      role="generator B (on); talk from (5, 3) facing north"),
    O("SOL_RUINS_GEN_B_OFF", "OBJ_EVENT_GFX_SHARD_GENERATOR_OFF", 5, 2, "S", LOCAL_0, "TODO_GeneratorB",
      role="generator B (off look); same tile, complementary flag"),
    O("SOL_RUINS_GEN_B_RACK_ON", "OBJ_EVENT_GFX_SHARD_FRAME", 4, 2, "S", "FLAG_SOL_RAID_B", "TODO_GeneratorB",
      role="the rack it feeds (lit), beside it in the north row"),
    O("SOL_RUINS_GEN_B_RACK_OFF", "OBJ_EVENT_GFX_SHARD_FRAME_DARK", 4, 2, "S", LOCAL_0, "TODO_GeneratorB",
      role="the rack, dim"),
    O("SOL_RUINS_GEN_B_GUARD", "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", 3, 2, "S", "FLAG_SOL_RAID_F",
      trainer="TRAINER_ECLIPSE_GRUNT_SOL_04", sight=2, role="RAID_GEN_B_GUARD: sees (3, 3), (3, 4)"),
    O("SOL_RUINS_GEN_B_CRATE_0", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 2, 2, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_GEN_B_CRATE_1", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 2, 4, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
]
ROOMS["ROOM_5"] = [
    O("SOL_RUINS_R5_GRUNT_05", "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", 2, 4, "N", "FLAG_SOL_RAID_F",
      trainer="TRAINER_ECLIPSE_GRUNT_SOL_05", sight=1, role="RAID_VAULT_WATCH: guards the stair to Room 6 (2,3)"),
    O("SOL_RUINS_R5_FRAME_0", "OBJ_EVENT_GFX_SHARD_FRAME", 3, 7, "S", "FLAG_SOL_RAID_F", "TODO_Frame"),
    O("SOL_RUINS_R5_FRAME_1", "OBJ_EVENT_GFX_SHARD_FRAME", 5, 7, "S", "FLAG_SOL_RAID_F", "TODO_Frame"),
    O("SOL_RUINS_R5_CRATE_0", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 4, 9, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_R5_CRATE_1", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 3, 5, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
]
ROOMS["ROOM_6"] = [
    O("SOL_RUINS_R6_CRATE_0", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 6, 6, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_R6_CRATE_1", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 6, 7, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_R6_CRYSTAL_0", "OBJ_EVENT_GFX_VIOLET_CRYSTAL", 6, 8, "S", "FLAG_SOL_RAID_F", "TODO_Crystal"),
]
ROOMS["ROOM_6_NORTHWEST_DEAD_END"] = [
    O("SOL_RUINS_GEN_C_ON", "OBJ_EVENT_GFX_SHARD_GENERATOR", 2, 2, "S", "FLAG_SOL_RAID_C", "TODO_GeneratorC",
      role="generator C (on); talk from (2, 3) facing north"),
    O("SOL_RUINS_GEN_C_OFF", "OBJ_EVENT_GFX_SHARD_GENERATOR_OFF", 2, 2, "S", LOCAL_0, "TODO_GeneratorC",
      role="generator C (off look); same tile, complementary flag"),
    O("SOL_RUINS_GEN_C_RACK_ON", "OBJ_EVENT_GFX_SHARD_FRAME", 3, 2, "S", "FLAG_SOL_RAID_C", "TODO_GeneratorC",
      role="the rack it feeds (lit), beside it in the north row"),
    O("SOL_RUINS_GEN_C_RACK_OFF", "OBJ_EVENT_GFX_SHARD_FRAME_DARK", 3, 2, "S", LOCAL_0, "TODO_GeneratorC",
      role="the rack, dim"),
    O("SOL_RUINS_GEN_C_GUARD", "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", 4, 2, "S", "FLAG_SOL_RAID_F",
      trainer="TRAINER_ECLIPSE_GRUNT_SOL_06", sight=2, role="RAID_GEN_C_GUARD: sees (4, 3), (4, 4)"),
    O("SOL_RUINS_GEN_C_CRATE_0", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 5, 2, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
    O("SOL_RUINS_GEN_C_CRATE_1", "OBJ_EVENT_GFX_ECLIPSE_CRATE", 5, 4, "S", "FLAG_SOL_RAID_F", "TODO_Crate"),
]
ROOMS["ROOM_7"] = (
    [O("SOL_RUINS_R7_BARRIER_%d" % i, "OBJ_EVENT_GFX_SHARD_BARRIER", x, 5, "S", "FLAG_SOL_RAID_D", "TODO_Barrier",
       role="the shard barrier, row z 5" if i == 0 else "") for i, x in enumerate(range(2, 9))]
    + [
        O("SOL_RUINS_R7_CYRUS", "OBJ_EVENT_GFX_CYRUS", 5, 4, "S", "FLAG_SOL_RAID_F", "TODO_CyrusBarrier",
          role="part 5: waits at the barrier, facing it"),
        O("SOL_RUINS_R7_LOOKER", "OBJ_EVENT_GFX_LOOKER", 8, 4, "W", LOCAL_0, "TODO_LookerVault",
          role="part 6: shown at 45-49 (runs in from the entry); OnTransition hides him otherwise"),
        O("SOL_RUINS_R7_INDRA", "OBJ_EVENT_GFX_INDRA", 5, 10, "S", "FLAG_SOL_RAID_G", "TODO_IndraVault",
          role="RAID_INDRA: at the main rack, back to the barrier; escapes (4,10)->(3,10)->(2,10)->west"),
        O("SOL_RUINS_R7_RUBBLE", "OBJ_EVENT_GFX_ROCK_SMASH", 2, 10, "S", LOCAL_2, "TODO_Rubble",
          role="the cave-in in front of the tunnel mouth, from 45 on (permanent)"),
    ]
    + [O("SOL_RUINS_R7_RACK_%d_LIT" % i, "OBJ_EVENT_GFX_SHARD_FRAME", x, z, "S", "FLAG_SOL_RAID_E", "TODO_Rack")
       for i, (x, z) in enumerate(((4, 11), (6, 11), (2, 6), (2, 7), (8, 6), (8, 7)))]
    + [O("SOL_RUINS_R7_RACK_%d_DARK" % i, "OBJ_EVENT_GFX_SHARD_FRAME_DARK", x, z, "S", LOCAL_1, "TODO_Rack")
       for i, (x, z) in enumerate(((4, 11), (6, 11), (2, 6), (2, 7), (8, 6), (8, 7)))]
    + [
        O("SOL_RUINS_R7_CRYSTAL_LIT", "OBJ_EVENT_GFX_VIOLET_CRYSTAL", 8, 8, "S", "FLAG_SOL_RAID_E", "TODO_Rack"),
        O("SOL_RUINS_R7_CRYSTAL_DARK", "OBJ_EVENT_GFX_VIOLET_CRYSTAL_DARK", 8, 8, "S", LOCAL_1, "TODO_Rack"),
    ]
    + [O("SOL_RUINS_R7_CRATE_%d" % i, "OBJ_EVENT_GFX_ECLIPSE_CRATE", x, z, "S", "FLAG_SOL_RAID_F", "TODO_Crate")
       for i, (x, z) in enumerate(((2, 4), (2, 8), (2, 9), (2, 11), (8, 9), (8, 11)))]
)

# the switch: a bg_event on the plinth (blocked terrain), read from Indra's tile facing south
BG_EVENTS = {"ROOM_7": [dict(script="TODO_MainRackSwitch", type=0, x=5, z=11, y=0,
                             player_facing_dir="BG_EVENT_DIR_SOUTH")]}

# coord triggers raid-scripts will want (listed in the doc; their scripts are raid-scripts' own)
COORDS = {
    "ROOM_1": [dict(x=5, z=10, note="first entry at 20: Cyrus scene (one tile in from the exit (5,11))")],
    "ROOM_7": [dict(x=x, z=6, note="first step past the barrier line sets 40 (var 33 + FLAG_SOL_RAID_D)")
               for x in range(2, 9)],
}

# local-flag rules (OnTransition), as functions of the state, -> set (hidden) when True
LOCAL_RULES = {
    "ROOM_1": {LOCAL_0: lambda s: not (20 <= s["var"] <= 49),     # raid crew of Room 1
               LOCAL_1: lambda s: s["var"] >= 20,                  # rope
               LOCAL_2: lambda s: s["var"] != 20},                 # Cyrus, first entry only
    "ROOM_2_NORTHEAST_DEAD_END": {LOCAL_0: lambda s: not (s["A"] and s["var"] <= 49)},
    "ROOM_4_SOUTHEAST_DEAD_END": {LOCAL_0: lambda s: not (s["B"] and s["var"] <= 49)},
    "ROOM_6_NORTHWEST_DEAD_END": {LOCAL_0: lambda s: not (s["C"] and s["var"] <= 49)},
    "ROOM_7": {LOCAL_0: lambda s: not (45 <= s["var"] <= 49),      # Looker
               LOCAL_1: lambda s: not (s["E"] and s["var"] <= 49),  # dark racks / core
               LOCAL_2: lambda s: s["var"] < 45},                  # rubble
}

STATES = collections.OrderedDict([
    ("pre-raid (0)", dict(var=0)),
    ("raid on, first entry (20)", dict(var=20)),
    ("inside, no generator off (30)", dict(var=30)),
    ("generator A off (31)", dict(var=31, A=1)),
    ("all off, barrier down (33)", dict(var=33, A=1, B=1, C=1, D=1)),
    ("vault (40)", dict(var=40, A=1, B=1, C=1, D=1)),
    ("Indra beaten and gone (45)", dict(var=45, A=1, B=1, C=1, D=1, G=1)),
    ("racks drained (45 + E)", dict(var=45, A=1, B=1, C=1, D=1, E=1, G=1)),
    ("raid done (50)", dict(var=50, A=1, B=1, C=1, D=1, E=1, F=1, G=1)),
])


def full_state(s):
    d = dict(var=0, A=0, B=0, C=0, D=0, E=0, F=0, G=0)
    d.update(s)
    return d


def visible(room, o, s):
    f = o["flag"]
    if f == "0":
        return True
    if f.startswith("FLAG_SOL_RAID_"):
        return not s[f[-1]]
    return not LOCAL_RULES[room][f](s)


# --------------------------------------------------------------------------------------------------------------
# stock data and checks
# --------------------------------------------------------------------------------------------------------------

def stock_perm(room, rev=R.BASE_REV):
    return mapdata.read_permissions(mapdata.unpack(C.git_file(rev, R.chunk_rel(R.ROOMS[room][2])))["permissions"])


def stock_events(room, rev=R.BASE_REV):
    return json.loads(C.git_file(rev, R.events_rel(room)))


INTENDED_BLOCKED = {"ROOM_7": {(5, 11)}, "ROOM_1": {(4, 11), (6, 11)}}   # build_dressing.py's permission changes


def walkable(room, perm, x, z):
    if (x, z) in INTENDED_BLOCKED.get(room, ()):
        return False
    return 0 <= x < 32 and 0 <= z < 32 and not perm[z][x] & 0x8000


def obstacles(room, s, ev, extra=()):
    occ = {(o["x"], o["z"]) for o in ROOMS.get(room, []) if visible(room, o, s)}
    occ |= {(o["x"], o["z"]) for o in ev["object_events"]
            if o["hidden_flag"] in ("0", 0) or o["graphics_id"] != "OBJ_EVENT_GFX_POKEBALL"}
    return occ | set(extra)


def bfs(room, perm, start, blocked, avoid=()):
    seen, todo = {start}, [start]
    while todo:
        x, z = todo.pop()
        for dx, dz in STEP.values():
            t = (x + dx, z + dz)
            if t in seen or t in blocked or t in avoid or not walkable(room, perm, *t):
                continue
            seen.add(t)
            todo.append(t)
    return seen


def sight_tiles(o):
    dx, dz = STEP[o["dir"]]
    return [(o["x"] + dx * k, o["z"] + dz * k) for k in range(1, o["sight"] + 1)]


def warp_arrivals(room, ev):
    return [(w["x"], w["z"]) for w in ev["warp_events"]]


def run_checks():
    res = []
    for room, objs in ROOMS.items():
        perm = stock_perm(room)
        ev = stock_events(room)
        name = R.ROOMS[room][0]
        warps = warp_arrivals(room, ev)
        for o in objs:
            ok = walkable(room, perm, o["x"], o["z"]) or (o["x"], o["z"]) in INTENDED_BLOCKED.get(room, ())
            if not ok:
                res.append((f"{name} {o['id']} at ({o['x']},{o['z']}) is on a stock blocked tile", False))
            if (o["x"], o["z"]) in warps and o["id"] != "SOL_RUINS_R1_ROPE":
                res.append((f"{name} {o['id']} stands on a warp tile", False))
            assert o["gfx"].startswith("OBJ_EVENT_GFX_"), o
        for sname, s0 in STATES.items():
            s = full_state(s0)
            vis = [o for o in objs if visible(room, o, s)]
            tiles = collections.Counter((o["x"], o["z"]) for o in vis)
            dup = [t for t, n in tiles.items() if n > 1]
            if dup:
                res.append((f"{name} [{sname}]: two visible objects on {dup}", False))
            # trainers' sight lines must be clear of visible objects
            for o in vis:
                if o["trainer"]:
                    st = sight_tiles(o)
                    occ = obstacles(room, s, ev) - {(o["x"], o["z"])}
                    bad = [t for t in st if t in occ or not walkable(room, perm, *t)]
                    if bad:
                        res.append((f"{name} [{sname}]: {o['id']} sight blocked at {bad}", False))
        res.append((f"{name}: {len(objs)} objects, tiles walkable (or intended), twins complementary in every state,"
                    f" sight lines clear", True))
    # gameplay: every generator's talk tile and every exit stays reachable; guards are unavoidable
    gens = {"ROOM_2_NORTHEAST_DEAD_END": ("A", (7, 3), "SOL_RUINS_GEN_A_GUARD"),
            "ROOM_4_SOUTHEAST_DEAD_END": ("B", (5, 3), "SOL_RUINS_GEN_B_GUARD"),
            "ROOM_6_NORTHWEST_DEAD_END": ("C", (2, 3), "SOL_RUINS_GEN_C_GUARD")}
    for room, (g, talk, guard) in gens.items():
        perm, ev = stock_perm(room), stock_events(room)
        s = full_state(dict(var=30))
        start = warp_arrivals(room, ev)[0]
        occ = obstacles(room, s, ev)
        reach = bfs(room, perm, start, occ)
        gd = next(o for o in ROOMS[room] if o["id"] == guard)
        sneak = bfs(room, perm, start, occ, avoid=set(sight_tiles(gd)))
        res.append((f"{R.ROOMS[room][0]}: generator {g} talk tile {talk} reachable from the warp {start}",
                    talk in reach))
        res.append((f"{R.ROOMS[room][0]}: no way to {talk} without crossing {guard}'s sight {sight_tiles(gd)}",
                    talk not in sneak))
    doors = {"ROOM_1": ((5, 11), (6, 3), "SOL_RUINS_R1_GRUNT_01"),
             "ROOM_3": ((6, 10), (6, 3), "SOL_RUINS_R3_GRUNT_03"),
             "ROOM_5": ((6, 3), (2, 3), "SOL_RUINS_R5_GRUNT_05")}
    for room, (start, door, grunt) in doors.items():
        perm, ev = stock_perm(room), stock_events(room)
        s = full_state(dict(var=30))
        occ = obstacles(room, s, ev)
        gd = next(o for o in ROOMS[room] if o["id"] == grunt)
        reach = bfs(room, perm, start, occ)
        sneak = bfs(room, perm, start, occ, avoid=set(sight_tiles(gd)))
        res.append((f"{R.ROOMS[room][0]}: door {door} reachable from {start} in the raid", door in reach))
        res.append((f"{R.ROOMS[room][0]}: {grunt} cannot be sneaked past on the way to {door}", door not in sneak))
    # every warp of every dressed room stays reachable in the raid and after it
    for room in ROOMS:
        perm, ev = stock_perm(room), stock_events(room)
        for sname in ("inside, no generator off (30)", "raid done (50)", "pre-raid (0)"):
            if sname == "pre-raid (0)" and room != "ROOM_1":
                continue
            s = full_state(STATES[sname])
            occ = obstacles(room, s, ev)
            ws = warp_arrivals(room, ev)
            start = ws[0]
            reach = bfs(room, perm, start, occ - {start})
            if room == "ROOM_7" and s["var"] < 33:
                continue
            miss = [w for w in ws if w not in reach and w not in occ]
            blockedw = [w for w in ws if w in occ]
            want_block = room == "ROOM_1" and s["var"] < 20
            ok = not miss and (blockedw == [(6, 3)] if want_block else not blockedw)
            res.append((f"{R.ROOMS[room][0]} [{sname}]: warps reachable {ws}" +
                        (" except the roped stair (6,3)" if want_block else ""), ok))
    # Room 7: barrier seals the vestibule while up; vault reachable when down; stock balls reachable after
    perm, ev = stock_perm("ROOM_7"), stock_events("ROOM_7")
    s = full_state(STATES["inside, no generator off (30)"])
    reach = bfs("ROOM_7", perm, (8, 3), obstacles("ROOM_7", s, ev))
    res.append(("R7 [30]: barrier up, the vestibule is sealed (no vault tile z >= 6 reachable)",
                not any(z >= 6 for _, z in reach)))
    s = full_state(STATES["vault (40)"])
    occ = obstacles("ROOM_7", s, ev)
    reach = bfs("ROOM_7", perm, (8, 3), occ)
    balls = [(o["x"], o["z"]) for o in ev["object_events"] if o["graphics_id"] == "OBJ_EVENT_GFX_POKEBALL"]
    adj = lambda t: any((t[0] + dx, t[1] + dz) in reach for dx, dz in STEP.values())
    res.append(("R7 [40]: barrier down, every stock item ball can be reached", all(adj(b) for b in balls)))
    res.append(("R7 [40]: the switch tile (5,10) is next to the plinth; Indra stands on it until 45",
                (5, 10) in occ))
    s = full_state(STATES["racks drained (45 + E)"])
    reach = bfs("ROOM_7", perm, (8, 3), obstacles("ROOM_7", s, ev))
    res.append(("R7 [45]: the switch tile (5,10) is reachable once Indra is gone", (5, 10) in reach))
    esc = [(4, 10), (3, 10), (2, 10)]
    s = full_state(STATES["vault (40)"])
    occ = obstacles("ROOM_7", s, ev)
    res.append(("R7 [40]: Indra's escape path (4,10),(3,10),(2,10) is free", not any(t in occ for t in esc)))
    return res


# --------------------------------------------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------------------------------------------

def event_json(o):
    gfx = o["gfx"]
    d = collections.OrderedDict()
    d["id"] = o["id"]
    d["graphics_id"] = gfx
    if o["trainer"]:
        d["movement_type"] = LOOK[o["dir"]]
        d["trainer_type"] = "TRAINER_TYPE_NORMAL"
    else:
        d["movement_type"] = LOOK[o["dir"]] if gfx in ("OBJ_EVENT_GFX_CYRUS", "OBJ_EVENT_GFX_LOOKER",
                                                        "OBJ_EVENT_GFX_INDRA") else "MOVEMENT_TYPE_NONE"
        d["trainer_type"] = "TRAINER_TYPE_NONE"
    d["hidden_flag"] = o["flag"]
    d["script"] = o["trainer"] or o["script"]
    d["initial_dir"] = DIRS[o["dir"]]
    d["data"] = [o["sight"]] if o["trainer"] else []
    d["movement_range_x"] = 0
    d["movement_range_z"] = 0
    d["x"] = o["x"]
    d["z"] = o["z"]
    d["y"] = 0
    return d


def snippets():
    out = collections.OrderedDict()
    for room, objs in ROOMS.items():
        out[room] = [event_json(o) for o in objs]
    return out


def ascii_map(room, s):
    perm, ev = stock_perm(room), stock_events(room)
    objs = [o for o in ROOMS.get(room, []) if visible(room, o, s)]
    mark = {}
    for w in ev["warp_events"]:
        mark[(w["x"], w["z"])] = "W"
    for o in ev["object_events"]:
        mark[(o["x"], o["z"])] = "b" if o["graphics_id"] == "OBJ_EVENT_GFX_POKEBALL" else "n"
    sym = {"GRUNT": "T", "GENERATOR": "G", "FRAME": "F", "CRYSTAL": "V", "CRATE": "K", "BARRIER": "X",
           "CYRUS": "Y", "LOOKER": "L", "INDRA": "I", "ROCK": "R", "ROPE": "~"}
    for o in objs:
        mark[(o["x"], o["z"])] = next((v for k, v in sym.items() if k in o["gfx"]), "o")
    xs = [x for z in range(32) for x in range(32) if walkable(room, perm, x, z) or (x, z) in mark]
    zs = [z for z in range(32) for x in range(32) if walkable(room, perm, x, z) or (x, z) in mark]
    lines = ["     " + "".join(f"{x:2d}" for x in range(min(xs) - 1, max(xs) + 2))]
    for z in range(min(zs) - 1, max(zs) + 2):
        row = ""
        for x in range(min(xs) - 1, max(xs) + 2):
            c = mark.get((x, z)) or ("." if walkable(room, perm, x, z) else
                                     ("P" if (x, z) in INTENDED_BLOCKED.get(room, ()) else "#"))
            row += " " + c
        lines.append(f"  {z:2d} " + row)
    return lines


def main():
    if "--json" in sys.argv:
        print(json.dumps(snippets(), indent=4))
        return
    if "--map" in sys.argv:
        s = full_state(dict(var=30))
        for room in ROOMS:
            st = s if room != "ROOM_7" else full_state(dict(var=30))
            print(R.ROOMS[room][0], room)
            print("\n".join(ascii_map(room, st)))
            print()
        return
    ok = True
    for name, good in run_checks():
        print(("PASS " if good else "FAIL ") + name)
        ok &= good
    print("ALL PASS" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
