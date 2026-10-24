"""DW headless kit: enter any rift at its entry state, move on any surface,
read the player's surface/tile from RAM, replay solution strings, detect
falls/catches/resets, read gDwPuzzleDebug, and write labelled frame strips.

Run with the Python 3.9 venv (the 3.12 venv's desmume is broken):

    SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python tools/distortion_world/emu/rifts_regress.py ...

Entry. Two ways in, both file-based (no live RAM writes to game state
except engine-a's documented gDwPuzzleTestMode gate):

1. Overworld entry (primary): the kit patches a copy of the
   battle-stage save in the file -- Location at the overworld rift
   approach tile, the pre-entry VAR_ARC2_PROGRESS, the rift's hide
   flag cleared, the story-true totem flags -- boots, and steps onto
   (Ravaged Path) or talks to (the rest) the rift object. The game's
   own warp sequence runs OnTransition, which activates the DW system
   (jump points, cameras, fall path). This is the only entry that
   fully works: a Continue boot into a DW map does not re-run
   OnTransition, so the DW system stays inactive there.
2. Direct boot (setstate): make_entry_save puts the player straight
   into the DW map at (20,12). It loads and the tiles read correctly,
   but the DW system is inactive (no jumps, no fall path), so it is
   for tile/pixel checks only, never for replay.

After boot, the requested progress is read back from RAM through
SaveData's page table and asserted, so a wrong save offset fails loudly
instead of silently playing the wrong state.

Save-file VarsFlags. In the .sav file the VarsFlags page sits at
partition_base + 3500 (the SaveTable pageInfo[4].location for this
save-table layout; verified by booting and comparing the file bytes with
the RAM VarsFlags block -- see notes in make_entry_save). A var lives at
(var_id - 0x4000) * 2; flags live at +580 (NUM_VARS = 290 u16 vars) as
flag_id // 8, bit flag_id % 8. Var/flag ids are parsed out of
generated/vars_flags.txt, the same file the C enum is generated from.

Player tile from RAM. sFieldSystem -> FieldSystem.playerAvatar (+0x3C) ->
PlayerAvatar.mapObject (+0x30) -> MapObject x (+100), y (+104), z (+108);
the game reports y/2 as the tile height (GetPlayerPos in ov9). Pointer
chain values are range-checked on every read.

Surface. Prefer gDwPuzzleDebug.surface when the engine-a debug struct is
present, active, and for this map. Otherwise infer it from the tile:
y == 1 is the floor, y == 10 is the ceiling, otherwise the wall fixed by
the rift's wall_x (x == 11 west wall on B1F clones, x == 49 east wall on
B4F clones). Surfaces occupy disjoint (x, y, z) ranges, so the inference
is unambiguous on today's maps.

Moves. One move = one FACE_* direction as pressed on the surface the
player stands on (FACE_UP = 0, DOWN = 1, LEFT = 2, RIGHT = 3; the D-pad
key of the same name). The (dx, dy, dz) step for a FACE_* on a surface
is the stock table in src/unk_0205F180.c (Unk_020EDB04..64):

    FLOOR:     UP (0,0,-1)  DOWN (0,0,+1)  LEFT (-1,0,0)  RIGHT (+1,0,0)
    WEST_WALL: UP (0,+1,0)  DOWN (0,-1,0)  LEFT (0,0,+1)  RIGHT (0,0,-1)
    EAST_WALL: UP (0,+1,0)  DOWN (0,-1,0)  LEFT (0,0,-1)  RIGHT (0,0,+1)
    CEILING:   UP (0,0,+1)  DOWN (0,0,-1)  LEFT (-1,0,0)  RIGHT (+1,0,0)

Solution strings are space-separated letters, e.g. "W W U U R ...".
Letters are U/D/L/R for the FACE_* directions; W/A/S/D are accepted as
aliases for U/L/D/R (W = up/forward). A compact string such as "UUDD"
is also accepted.

gDwPuzzleDebug. Layout is engine-a's include/overlay009/dw_puzzle.h
(DwPuzzleDebug): mapHeader @0, active @4, player @8/10/12, surface @14,
tile state @15, groupBits @20, groupDisplayBits @24, sigilBits @28,
checkpointIndex @32, checkpoint @36/38/40, fallCount @44, frameCount @48,
slideActive @52, slideDir @56, slideTarget @60/62/64, lastEvent @68,
lastEventFrame @72, lastEventGroup @76, flashFrames @80,
resetGeneration @84, stones (8 x 8 bytes) @88, stoneCount @152,
shadowPhase @156, shadow @160/162/164, echo @166/168/170. Size 172,
plus stoneStates[] (RESTING 0, FALLING 1, LANDED 2) appended by
engine-a/b after the prefix; the reader takes the symbol's xMAP size
and parses the tail tolerantly, so growth never breaks it.
Every field is read through the xMAP symbol of the same build; when the
symbol is absent (pre-engine-a ROM) debug() returns None and the kit
falls back to tile inference. The layout is sanity-checked on read
(mapHeader is this map or 0, active is 0/1, surface <= 4).

Only one Emu may exist per process (py-desmume segfaults on a second
DeSmuME()). One DwSession per process; rifts_regress.py spawns one
worker process per rift.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import struct
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "tools" / "battle_stage" / "emu"))
sys.path.insert(0, str(_REPO / "tools"))

from emu import Emu, contact_sheet, dedupe, read_xmap  # noqa: E402
from make_save import fix_crc, newest_partition  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FACE_UP, FACE_DOWN, FACE_LEFT, FACE_RIGHT = 0, 1, 2, 3
FACE_KEY = {FACE_UP: "UP", FACE_DOWN: "DOWN", FACE_LEFT: "LEFT", FACE_RIGHT: "RIGHT"}
FACE_LETTER = {FACE_UP: "U", FACE_DOWN: "D", FACE_LEFT: "L", FACE_RIGHT: "R"}
LETTER_FACE = {"U": FACE_UP, "D": FACE_DOWN, "L": FACE_LEFT, "R": FACE_RIGHT,
               "W": FACE_UP}
SURF_FLOOR, SURF_WEST, SURF_EAST, SURF_CEIL, SURF_INVALID = 0, 1, 2, 3, 4
SURF_NAME = {0: "floor", 1: "west_wall", 2: "east_wall", 3: "ceiling", 4: "invalid"}

# (dx, dy, dz) per FACE_* (UP, DOWN, LEFT, RIGHT), from src/unk_0205F180.c.
DIR_DELTA = {
    SURF_FLOOR: ((0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0)),
    SURF_WEST: ((0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)),
    SURF_EAST: ((0, 1, 0), (0, -1, 0), (0, 0, -1), (0, 0, 1)),
    SURF_CEIL: ((0, 0, 1), (0, 0, -1), (-1, 0, 0), (1, 0, 0)),
}

# DwPuzzleTileState / DwPuzzleEvent (dw_puzzle.h).
TILE_DEFAULT, TILE_SOLID, TILE_VOID, TILE_BLOCKED = 0, 1, 2, 3
EV_NONE, EV_SIGIL, EV_RUNE, EV_CUR_START, EV_CUR_STOP, EV_CHECKPOINT, EV_FALL, EV_RESPAWN, EV_RESET = range(9)
EV_NAME = {0: "none", 1: "sigil", 2: "rune", 3: "current_start", 4: "current_stop",
           5: "checkpoint", 6: "fall", 7: "respawn", 8: "reset"}

VARS_START = 0x4000
VARS_FLAGS_FILE_OFFSET = 3500   # SaveTable pageInfo[4].location; see module docstring.
NUM_VARS = 290
FLAGS_BYTE_OFFSET = VARS_FLAGS_FILE_OFFSET + NUM_VARS * 2
LOCATION_OFFSET = 0x1280        # Location {mapId, warpId, x, z, dir}, s32 each.
DIR_WEST = 2



BASE_SAVE = _REPO / "tools" / "battle_stage" / "emu" / "saves" / "eterna_forest_grass.sav"


class Rift:
    """One DW rift as the harness sees it: entry state, wall geometry, goal."""

    def __init__(self, key, map_header, map_id, progress, var="VAR_ARC2_PROGRESS",
                 entry=(20, 12), wall_x=None, wall_side=None, totem_tile=None,
                 goal_tile=None, flags=(), clear_flags=(), extra_vars=None,
                 checkpoint_tile=(20, 12), notes=""):
        self.key = key
        self.map_header = map_header
        self.map_id = map_id
        self.progress = progress          # entry state of the progress var
        self.var = var
        self.entry = entry
        self.wall_x = wall_x              # x of the wall surface, if any
        self.wall_side = wall_side        # SURF_WEST / SURF_EAST / None
        self.totem_tile = totem_tile      # (x, y, z) whose step starts the totem
        self.goal_tile = goal_tile or totem_tile
        self.flags = tuple(flags)         # flags the story has set by entry
        self.clear_flags = tuple(clear_flags)
        self.extra_vars = dict(extra_vars or {})
        self.checkpoint_tile = checkpoint_tile
        self.notes = notes


# Totem flags are set by the story before the Lost Tower's second visit;
# the ghost acts there need them, and the visit-2 flags below are the
# story-true state (all four earlier totems calmed).
RIFTS = {
    # Arc 1 seams: the tutorial wall-walk. No totem battle; the goal is
    # stepping off the wall onto the far ledge (12, 23).
    "arc1": Rift("arc1", "MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS", 595, 5,
                 var="VAR_ARC1_PROGRESS", wall_x=11, wall_side=SURF_WEST,
                 goal_tile=(12, 1, 23), notes="tutorial; no totem"),
    "rp": Rift("rp", "MAP_HEADER_DW_RAVAGED_PATH", 596, 14,
               wall_x=11, wall_side=SURF_WEST, totem_tile=(14, 1, 23)),
    "ef": Rift("ef", "MAP_HEADER_DW_ETERNA_FOREST", 597, 24,
               wall_x=49, wall_side=SURF_EAST, totem_tile=(45, 10, 41),
               checkpoint_tile=(40, 1, 22),
               notes="honeycomb fall returns to the hive (40,22)"),
    "r214": Rift("r214", "MAP_HEADER_DW_ROUTE_214", 598, 62,
                 wall_x=49, wall_side=SURF_EAST, totem_tile=(49, 10, 45)),
    "r213": Rift("r213", "MAP_HEADER_DW_ROUTE_213", 599, 83,
                 wall_x=49, wall_side=SURF_EAST, totem_tile=(46, 10, 46)),
    # Lost Tower visit 1 (92): the vein at (13, 23) is the goal; the
    # shadow wall ends the visit. Visit 2 (94): the Spiritomb. The
    # visit-2 entry state is the story-true one: all four earlier totems
    # calmed, so the ghost acts play in full.
    "lt1": Rift("lt1", "MAP_HEADER_DW_LOST_TOWER", 600, 92,
                wall_x=11, wall_side=SURF_WEST, goal_tile=(13, 1, 23)),
    "lt2": Rift("lt2", "MAP_HEADER_DW_LOST_TOWER", 600, 94,
                wall_x=11, wall_side=SURF_WEST, totem_tile=(37, 1, 22),
                flags=("FLAG_TOTEM_HITMONLEE_DEFEATED", "FLAG_TOTEM_VESPIQUEN_DEFEATED",
                       "FLAG_TOTEM_SKARMORY_DEFEATED", "FLAG_TOTEM_LAPRAS_DEFEATED")),
}

# Recorded solutions (move strings; see parse_moves). Verified by
# rifts_regress.py against the ROM; see that file's header for how each
# route was derived.
# Solutions are verified by rifts_regress.py; see its header for how each
# route was derived (docs + emulator exploration). Key: L/R/U/D are
# FACE_* presses on the surface the player stands on; A taps A.
SOLUTIONS = {
    # Arc1: Lx5 to (15,12), Dx2 to (15,14), Lx3 to (12,14), L onto
    # the wall (11,2,13), Lx9 along the bottom row to z22, L off
    # to (12,23).
    "arc1": "L L L L L D D L L L L L L L L L L L L L D",
    # RP: Lx5 to (15,12) [the walkway is (15..20,12)], Dx2 to the
    # ledge (15,14) -> Lx3 to (12,14), L onto the wall (11,2,13),
    # Lx6 to the fork (z19), Ux2 up the seam (y4), Lx3 to z22,
    # Dx2, D off (the off-jump template is dir DOWN) to (12,23); the
    # two steps east.
    "rp": "L L L L L D D L L L L L L L L L L U U L L L D D D R R",
    # EF: west to the fold (17,12), hive (40,22), east to (48,22), RIGHT
    # onto the east wall (49,1,21), RIGHT to z27, climb to y9, UP onto
    # the ceiling, UP to z32, LEFT to x45, UP through the honeycomb to z41.
    # The honeycomb timing is handled by rifts_regress (wait for a solid
    # window); the raw string below is the shape, not the final timing.
    "ef": "L L L R R R R R R R R R R R R R U U U U U U U U U U U U U U L L L L U U U U U U U U U",
    # R214/R213: entry steps out to (17,12); floor route found by
    # emulator exploration (see rifts_regress.py); wall/ceiling as EF.
    # PLACEHOLDER -- replaced by exploration below (regress fills it in).
    "r214": "D D D D D D D D D D R R R R R R R R R R R R R R R U U U U U U U U U U U U U U U U U U",
    "r213": "D D D D D D D D D D R R R R R R R R R R R R R R R U U U U U U U U U U U U U U U U U U",
    # LT visit 1: as RP to (12,23), then RIGHT to the vein (13,23).
    "lt1": "L L L L L L L L D D L L L L L L U U L L L D D L R R R",
    # LT visit 2: as visit 1 past the shadow wall, then east along the
    # deeper ledge to (20,22), hop the stones to (32,22); Skarmory's
    # carry (scripted) lands on the island (37,22). PLACEHOLDER for the
    # hop inputs -- replaced by exploration.
    "lt2": "L L L L L L L L D D L L L L L L U U L L L D D L R R R R R R R R",
}


# ---------------------------------------------------------------------------
# generated/vars_flags.txt ids
# ---------------------------------------------------------------------------

def parse_ids(path=None):
    """name -> id, evaluating the vars_flags enum (assignments reset the
    sequence, bare names increment). Verified against the generated
    header (build/generated/vars_flags.h): VAR_ARC2_PROGRESS == 16495
    (0x406F -- docs/arc2/registry.md's 0x4070 is stale),
    FLAG_TOTEM_HITMONLEE_DEFEATED == 2304."""
    path = path or (_REPO / "generated" / "vars_flags.txt")
    ids, value = {}, 0
    for line in pathlib.Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            name, expr = (p.strip() for p in line.split("=", 1))
            value = int(expr, 0) if re.fullmatch(r"[0-9][0-9A-Fa-fxX]*", expr) else ids[expr]
            ids[name] = value
            value += 1
        else:
            ids[line] = value
            value += 1
    assert ids["VAR_ARC2_PROGRESS"] == 16495, ids["VAR_ARC2_PROGRESS"]
    assert ids["FLAG_TOTEM_HITMONLEE_DEFEATED"] == 2304, ids["FLAG_TOTEM_HITMONLEE_DEFEATED"]
    return ids


# ---------------------------------------------------------------------------
# Save patching (file-based entry)
# ---------------------------------------------------------------------------

def _find_player_object(raw, base):
    """Offset of the player's MapObjectSave in the newest partition:
    localID 0xFF at +8, x/z at +0x26/+0x2A matching the Location."""
    _, _, x, z, _ = struct.unpack_from("<iiiii", raw, base + LOCATION_OFFSET)
    for off in range(base, base + 0xCF2C - 0x50, 2):
        if raw[off + 8] == 0xFF and struct.unpack_from("<h", raw, off + 0x26)[0] == x \
                and struct.unpack_from("<h", raw, off + 0x2A)[0] == z \
                and struct.unpack_from("<h", raw, off + 0x20)[0] == x:
            return off
    raise RuntimeError("player map object not found in save")


def make_entry_save(rift, out_path, base_save=None, extra_vars=None, set_flags=(),
                    clear_flags=(), ids=None):
    """Copy `base_save`, put the player at the rift entry (map, tile,
    facing west) and set the entry progress / flags in the file. Returns
    the output path. The caller verifies the values back from RAM after
    boot (DwSession.boot asserts the progress var)."""
    ids = ids or parse_ids()
    raw = bytearray(pathlib.Path(base_save or BASE_SAVE).read_bytes())
    base = newest_partition(raw)
    obj = _find_player_object(raw, base)
    x, z = rift.entry
    struct.pack_into("<iiiii", raw, base + LOCATION_OFFSET, rift.map_id, -1, x, z, DIR_WEST)
    struct.pack_into("<bbb", raw, obj + 0x0C, DIR_WEST, DIR_WEST, DIR_WEST)
    for off in (0x20, 0x26):
        struct.pack_into("<h", raw, obj + off, x)
    for off in (0x24, 0x2A):
        struct.pack_into("<h", raw, obj + off, z)
    vars_to_set = {rift.var: rift.progress, **rift.extra_vars, **(extra_vars or {})}
    for name, val in vars_to_set.items():
        vid = ids[name]
        assert VARS_START <= vid < VARS_START + NUM_VARS, (name, vid)
        struct.pack_into("<H", raw, base + VARS_FLAGS_FILE_OFFSET + (vid - VARS_START) * 2, val)
    for name in tuple(rift.flags) + tuple(set_flags):
        fid = ids[name]
        raw[base + FLAGS_BYTE_OFFSET + fid // 8] |= 1 << (fid % 8)
    for name in tuple(rift.clear_flags) + tuple(clear_flags):
        fid = ids[name]
        raw[base + FLAGS_BYTE_OFFSET + fid // 8] &= ~(1 << (fid % 8)) & 0xFF
    fix_crc(raw, base)
    pathlib.Path(out_path).write_bytes(raw)
    return str(out_path)


# ---------------------------------------------------------------------------
# Overworld entry: save at the overworld rift tile, step in
# ---------------------------------------------------------------------------

class OverworldRift:
    """How to enter a DW rift through the game's own rift object.
    method 'step': a coord event fires when the player steps onto the
    rift tile (Ravaged Path). method 'talk': press A facing the rift
    object, then answer the prompt (Eterna Forest: Yes; the others
    warp at once). approach: where the player stands; approach_dir:
    the facing enum (0 north, 1 south, 2 west, 3 east); walk_in: the
    moves from the approach tile onto the rift tile (step method).
    The RP approach is the bottom of the stairs (19,50): the rift
    tile (19,45) sits at height 2 and the stairs raise the player as
    they walk up; teleporting straight to (19,46) leaves the player
    at the wrong height and the rift never triggers."""

    def __init__(self, key, ow_map_id, approach, approach_dir, rift_tile,
                 method, trigger, pre_progress, clear_flags=(), walk_in=(),
                 rift_object=None):
        self.key = key
        self.ow_map_id = ow_map_id
        self.approach = approach
        self.approach_dir = approach_dir
        self.rift_tile = rift_tile
        self.method = method
        self.trigger = trigger
        self.pre_progress = pre_progress
        self.clear_flags = tuple(clear_flags)
        self.walk_in = list(walk_in)
        # (localID, gfx, hide flag name, script, x, z, dir) for talk
        # rifts: the object the player presses A on.
        self.rift_object = rift_object


OVERWORLD_RIFTS = {
    # RP: walk up the stairs to the coord event at (19,45), progress 13/14.
    "rp": OverworldRift("rp", 254, (19, 50), 0, (19, 45), "step", FACE_UP, 13,
                        clear_flags=("FLAG_UNK_0x003E",),
                        walk_in=[FACE_UP] * 5),
    # EF: object at (84,38); stand (84,37) facing south, A, then Yes.
    "ef": OverworldRift("ef", 203, (84, 37), 1, (84, 38), "talk", None, 23,
                        clear_flags=("FLAG_UNK_0x0031",),
                        rift_object=(27, 296, "FLAG_UNK_0x0031", 15, 84, 38, 1)),
    # Route 214: object at (726,664); stand (726,665) facing north, A.
    "r214": OverworldRift("r214", 380, (726, 665), 0, (726, 664), "talk", None, 61,
                          clear_flags=("FLAG_UNK_0x0030",),
                          rift_object=(28, 296, "FLAG_UNK_0x0030", 5, 726, 664, 1)),
    # Route 213: object at (715,830); stand (715,831) facing north, A.
    "r213": OverworldRift("r213", 373, (715, 831), 0, (715, 830), "talk", None, 83,
                          clear_flags=("FLAG_UNK_0x0038",),
                          rift_object=(42, 296, "FLAG_UNK_0x0038", 9, 715, 830, 1)),
    # Lost Tower 2F: object at (6,8); stand (7,8) facing west, A.
    # Visit 1 pre-progress 92, visit 2 pre-progress 94.
    "lt1": OverworldRift("lt1", 358, (7, 8), 2, (6, 8), "talk", None, 92,
                         clear_flags=("FLAG_ARC2_HEARTHOME_B",),
                         rift_object=(2, 296, "FLAG_ARC2_HEARTHOME_B", 1, 6, 8, 1)),
    "lt2": OverworldRift("lt2", 358, (7, 8), 2, (6, 8), "talk", None, 94,
                         clear_flags=("FLAG_ARC2_HEARTHOME_B",),
                         rift_object=(2, 296, "FLAG_ARC2_HEARTHOME_B", 1, 6, 8, 1)),
}


# The save's object list: FieldOverworldSave starts at SaveTable
# pageInfo[11].location = partition_base + 10328: 64 MapObjectSave
# entries of 80 bytes. A Continue boot loads exactly this list, so a
# rift object that was hidden when the base save was written is not
# there; for talk rifts the kit writes it back (see
# _append_rift_object). File offset verified: slot 0 is the player
# (localID 0xFF, matching the Location) in the base save.
OBJECT_LIST_FILE_OFFSET = 10328
MAP_OBJECT_SAVE_SIZE = 80
MAP_OBJECT_SAVE_COUNT = 64


def _append_rift_object(raw, base, ow, ids):
    """Replace the saved object list (stale: the base save's map,
    captured before the rift was active) with the player plus the
    rift object. The template is the first non-player, non-zero entry
    in the base save -- a working static object's status/unk fields,
    copied verbatim, with the rift's own id/gfx/flag/script/coords
    patched in. The rift object's hide flag is cleared by the caller,
    so the game's own LoadObjects spawns it."""
    lst = base + OBJECT_LIST_FILE_OFFSET
    template = None
    for i in range(1, MAP_OBJECT_SAVE_COUNT):
        e = raw[lst + i * MAP_OBJECT_SAVE_SIZE:
                lst + (i + 1) * MAP_OBJECT_SAVE_SIZE]
        if struct.unpack_from("<I", e, 0)[0] != 0 and e[8] != 0xFF:
            template = bytes(e)
            break
    if template is None:
        raise RuntimeError("no template object in base save")
    for i in range(1, MAP_OBJECT_SAVE_COUNT):
        raw[lst + i * MAP_OBJECT_SAVE_SIZE:
            lst + (i + 1) * MAP_OBJECT_SAVE_SIZE] = bytes(MAP_OBJECT_SAVE_SIZE)
    local_id, gfx, flag_name, script, x, z, direction = ow.rift_object
    e = bytearray(template)
    e[8] = local_id
    e[9] = 0  # MOVEMENT_TYPE_NONE
    e[10] = 0
    e[11] = 0
    e[12] = direction
    e[13] = direction
    e[14] = direction
    struct.pack_into("<H", e, 18, gfx)
    struct.pack_into("<H", e, 20, 0)  # TRAINER_TYPE_NONE
    struct.pack_into("<H", e, 22, ids[flag_name])
    struct.pack_into("<H", e, 24, script)
    struct.pack_into("<h", e, 32, x)
    struct.pack_into("<h", e, 34, 0)
    struct.pack_into("<h", e, 36, z)
    struct.pack_into("<h", e, 38, x)
    struct.pack_into("<h", e, 40, 0)
    struct.pack_into("<h", e, 42, z)
    raw[lst + MAP_OBJECT_SAVE_SIZE:lst + 2 * MAP_OBJECT_SAVE_SIZE] = e


def make_overworld_save(rift_key, out_path, base_save=None, ids=None):
    """Save standing at the overworld rift approach tile, at the
    pre-entry progress, with the rift's hide flag cleared. No DW
    persisted-features patch: the rift object's own warp sequence
    runs OnTransition and activates the DW system."""
    ids = ids or parse_ids()
    ow = OVERWORLD_RIFTS[rift_key]
    rift = RIFTS[rift_key]
    raw = bytearray(pathlib.Path(base_save or BASE_SAVE).read_bytes())
    base = newest_partition(raw)
    obj = _find_player_object(raw, base)
    x, z = ow.approach
    struct.pack_into("<iiiii", raw, base + LOCATION_OFFSET, ow.ow_map_id, -1, x, z,
                     ow.approach_dir)
    struct.pack_into("<bbb", raw, obj + 0x0C, ow.approach_dir, ow.approach_dir,
                     ow.approach_dir)
    for off in (0x20, 0x26):
        struct.pack_into("<h", raw, obj + off, x)
    for off in (0x24, 0x2A):
        struct.pack_into("<h", raw, obj + off, z)
    struct.pack_into("<H", raw, base + VARS_FLAGS_FILE_OFFSET
                     + (ids["VAR_ARC2_PROGRESS"] - VARS_START) * 2, ow.pre_progress)
    for name in ow.clear_flags:
        fid = ids[name]
        raw[base + FLAGS_BYTE_OFFSET + fid // 8] &= ~(1 << (fid % 8)) & 0xFF
    # The rift workstreams' own flags (totem calms for LT visit 2) must
    # be set before entry, as the story has them by then.
    for name in rift.flags:
        fid = ids[name]
        raw[base + FLAGS_BYTE_OFFSET + fid // 8] |= 1 << (fid % 8)
    for name in rift.clear_flags:
        fid = ids[name]
        raw[base + FLAGS_BYTE_OFFSET + fid // 8] &= ~(1 << (fid % 8)) & 0xFF
    if ow.rift_object is not None:
        _append_rift_object(raw, base, ow, ids)
    fix_crc(raw, base)
    pathlib.Path(out_path).write_bytes(raw)
    return str(out_path)


# ---------------------------------------------------------------------------
# Move strings
# ---------------------------------------------------------------------------

INTERACT, WAIT = -2, -3  # special replay tokens: tap A / wait 60 frames

def parse_moves(text):
    """'W W U U R ...' / 'UUDD' / 'U, D, L' -> [FACE_* or INTERACT/WAIT].
    Letters are U/D/L/R for the FACE_* directions; W is an alias for U
    (up/forward). A taps A (talk / advance / confirm), '.' waits."""
    if isinstance(text, (list, tuple)):
        return list(text)
    moves = []
    for tok in re.findall(r"[A-Za-z.]", str(text).replace(",", " ")):
        tok = tok.upper()
        if tok == "A":
            moves.append(INTERACT)
        elif tok == ".":
            moves.append(WAIT)
        elif tok in LETTER_FACE:
            moves.append(LETTER_FACE[tok])
        elif tok in FACE_LETTER.values():
            moves.append({v: k for k, v in FACE_LETTER.items()}[tok])
        elif tok == "W":
            moves.append(FACE_UP)
        else:
            raise ValueError(f"bad move letter {tok!r} in {text!r}")
    return moves


def format_moves(moves):
    out = []
    for m in moves:
        out.append("A" if m == INTERACT else ("." if m == WAIT else FACE_LETTER[m]))
    return " ".join(out)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

RAM_BASE, RAM_END = 0x02000000, 0x02400000


def _in_ram(addr):
    return RAM_BASE <= addr < RAM_END


class DwSession:
    """One emulator + one rift. One per process."""

    def __init__(self, rom, xmap=None, outdir="/tmp/dwp/harness", verbose=False):
        self.rom = str(rom)
        self.xmap = xmap or str(pathlib.Path(rom).with_suffix("")) + ".xMAP"
        # The xMAP sits next to the build output, not the ROM copy.
        if not os.path.exists(self.xmap):
            self.xmap = str(_REPO / "build" / "main.nef.xMAP")
        self.syms = read_xmap(self.xmap) if os.path.exists(self.xmap) else {}
        self.outdir = pathlib.Path(outdir)
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.emu = None
        self.rift = None
        self.verbose = verbose
        self._pageinfo = None
        self._save_ptr_val = None
        self._debug_addr = None

    # -- lifecycle ------------------------------------------------------

    def boot_overworld_rift(self, rift_key, save_path=None, test_mode=False,
                            boot_timeout=2400):
        """Enter through the overworld rift object (the primary entry):
        boot at the approach tile, trigger the rift, wait for the
        warp into the DW map, and assert the entry state. For 'talk'
        rifts the prompt is answered Yes (Eterna Forest) or the warp
        runs at once (the rest)."""
        ow = OVERWORLD_RIFTS[rift_key]
        rift = RIFTS[rift_key]
        self.rift = rift
        sav = save_path or str(self.outdir / f"ow_{rift.key}.sav")
        make_overworld_save(rift_key, sav)
        self.emu = Emu(self.rom, sav)
        if not self.emu.boot(timeout=boot_timeout):
            raise RuntimeError(f"boot failed for overworld rift {rift.key}")
        self.emu.run(60)
        if ow.method == "step":
            for face in ow.walk_in:
                self.step(face, advance_text=True)
        else:
            # Face the rift object and press A; Eterna Forest asks
            # Yes/No (Yes is the default, A confirms it).
            self.step(INTERACT, advance_text=True)
        # The rift script (fanfare, fades, warp) still runs after the
        # trigger step: keep tapping A (menu answers, dialogue) until
        # the map changes or the wait expires.
        start = self.emu.frame
        while self.emu.frame - start < 1800:
            if self.current_map() == rift.map_id:
                break
            self.emu.tap("A", 30)
        if self.current_map() != rift.map_id:
            raise RuntimeError(
                f"rift warp did not land in map {rift.map_id} "
                f"(now {self.current_map()}, tile {self.player_tile()})")
        self.wait_settled(timeout=900)
        # The entry script's message appears after a delay, so let it
        # show, clear it, and prove the game answers input before
        # replay starts (a press right after a warp is dropped).
        self.emu.run(300)
        self.pump_text(max_frames=900)
        self.wait_settled(timeout=300)
        if not self.probe_controllable():
            raise RuntimeError("game did not become controllable after entry")
        if self.player_tile() != (rift.entry[0], 1, rift.entry[1]):
            raise RuntimeError(f"entry tile moved to {self.player_tile()}")
        if test_mode:
            self.set_test_mode(True)
        got = self.var(rift.var)
        if got != rift.progress:
            raise RuntimeError(f"entry var {rift.var} = {got}, want {rift.progress}")
        return self

    def boot_rift(self, rift_key, save_path=None, extra_vars=None, set_flags=(),
                  clear_flags=(), test_mode=False, boot_timeout=2400):
        """Direct boot into the DW map (setstate). Loads, but the DW
        system stays inactive (Continue does not run OnTransition):
        for tile/pixel checks only. Use boot_overworld_rift for replay.
        test_mode sets engine-a's gDwPuzzleTestMode RAM gate (read back)."""
        rift = RIFTS[rift_key] if isinstance(rift_key, str) else rift_key
        self.rift = rift
        sav = save_path or str(self.outdir / f"entry_{rift.key}.sav")
        make_entry_save(rift, sav, extra_vars=extra_vars, set_flags=set_flags,
                        clear_flags=clear_flags)
        self.emu = Emu(self.rom, sav)
        if not self.emu.boot(timeout=boot_timeout):
            raise RuntimeError(f"boot failed for rift {rift.key}")
        self.emu.run(60)
        # The rift scripts may move the player off the entry tile
        # (Route 214/213 step out of the trees to (17,12)) and may
        # open entry dialogue (Ravaged Path's Cyrus line). Let the
        # scene finish and clear its dialogue before asserting state.
        self.wait_settled(timeout=900)
        self.pump_text(max_frames=900)
        self.wait_settled(timeout=300)
        if test_mode:
            self.set_test_mode(True)
        got = self.var(rift.var)
        if got != rift.progress:
            raise RuntimeError(f"entry var {rift.var} = {got}, want {rift.progress}")
        return self

    def close(self):
        if self.emu is not None:
            self.emu.close()
            self.emu = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- low-level RAM --------------------------------------------------

    def _read32(self, addr):
        return struct.unpack("<I", self.emu.read(addr, 4))[0]

    def _save_ptr(self):
        if self._save_ptr_val is None:
            addr = self.syms["sSaveDataPtr"][0]
            self._save_ptr_val = self._read32(addr)
            if not _in_ram(self._save_ptr_val):
                raise RuntimeError(f"sSaveDataPtr {self._save_ptr_val:#x} outside RAM")
        return self._save_ptr_val

    def _pageinfo_addr(self):
        """SaveData.pageInfo: validated candidate, else a full RAM scan
        for the page-table signature (pageIDs 0..7, sane sizes, monotone
        locations). The scan is the fallback, not the path."""
        if self._pageinfo is not None:
            return self._pageinfo
        sd = self._save_ptr()
        cand = sd + 20 + 0x20000 + 4 + 8 + 4
        if self._pageinfo_valid(cand):
            self._pageinfo = cand
            return cand
        ram = self.emu.ram()
        for o in range(0, len(ram) - 16 * 8, 4):
            if self._pageinfo_valid_ram(ram, o):
                self._pageinfo = RAM_BASE + o
                return self._pageinfo
        raise RuntimeError("SaveData.pageInfo not found in RAM")

    def _pageinfo_valid(self, addr):
        if not _in_ram(addr):
            return False
        try:
            data = self.emu.read(addr, 16 * 8)
        except Exception:
            return False
        return self._pageinfo_valid_ram(data, 0)

    @staticmethod
    def _pageinfo_valid_ram(data, o):
        prev = -1
        for i in range(8):
            pid, size, loc, _chk, bid = struct.unpack_from("<I I I H H", data, o + i * 16)
            if pid != i or not 0 < size <= 0x8000 or not 0 <= loc <= 0x20000 \
                    or bid > 1 or loc < prev:
                return False
            prev = loc
        return True

    def _vars_flags_addr(self):
        pi = self._pageinfo_addr()
        _pid, size, loc = struct.unpack("<I I I", self.emu.read(pi + 4 * 16, 12))
        if size != 948:
            raise RuntimeError(f"VarsFlags page size {size}, want 948")
        return self._save_ptr() + 20 + loc

    def var(self, name_or_id, ids=None):
        """Current value of a save var, read from RAM (read-only)."""
        vid = name_or_id if isinstance(name_or_id, int) else parse_ids()[name_or_id]
        addr = self._vars_flags_addr() + (vid - VARS_START) * 2
        return struct.unpack("<H", self.emu.read(addr, 2))[0]

    def flag(self, name, ids=None):
        fid = name if isinstance(name, int) else parse_ids()[name]
        addr = self._vars_flags_addr() + NUM_VARS * 2 + fid // 8
        return (self.emu.read(addr, 1)[0] >> (fid % 8)) & 1

    def set_test_mode(self, enabled):
        """Write engine-a's gDwPuzzleTestMode gate (its documented
        harness entry point). Read back and assert."""
        if "gDwPuzzleTestMode" not in self.syms:
            raise RuntimeError("gDwPuzzleTestMode not in xMAP (pre-engine-a ROM?)")
        addr = self.syms["gDwPuzzleTestMode"][0]
        self.emu.write(addr, struct.pack("<I", 1 if enabled else 0))
        if self._read32(addr) != (1 if enabled else 0):
            raise RuntimeError("gDwPuzzleTestMode write did not stick")

    # -- player state ---------------------------------------------------

    def player_tile(self):
        """(x, y, z) from the player's MapObject (y already halved, as
        the game's GetPlayerPos reports it). Raises on a bad chain:
        use player_tile_or_none() while a warp is in flight."""
        t = self.player_tile_or_none()
        if t is None:
            raise RuntimeError("player tile unreadable (bad MapObject chain)")
        return t

    def _map_object_addr(self):
        """The player's MapObject address, or None while the chain is
        torn down during a warp. MapObject: x @+100, y @+104, z @+108,
        facingDir @+40 (DIR: 0 north, 1 south, 2 west, 3 east)."""
        try:
            fs = self._read32(self.syms["sFieldSystem"][0])
            if not _in_ram(fs):
                return None
            avatar = self._read32(fs + 0x3C)
            if not _in_ram(avatar):
                return None
            mobj = self._read32(avatar + 0x30)
            if not _in_ram(mobj):
                return None
            return mobj
        except Exception:
            return None

    def facing(self):
        """The player's facing dir (0 north, 1 south, 2 west, 3 east),
        or None if the chain is down."""
        mobj = self._map_object_addr()
        if mobj is None:
            return None
        try:
            return self._read32(mobj + 40)
        except Exception:
            return None

    def probe_controllable(self, tries=3):
        """True once the game answers input. A press right after a
        warp or an entry script is dropped by the game, so replay
        must not start until this passes: turn east and back west
        (short taps that only turn, never step) and check the facing
        actually changed. Only runs when the player faces west, as
        after a DW entry warp."""
        for _ in range(tries):
            if self.facing() != FACE_LEFT:
                return False
            self.emu.hold("RIGHT", 6, 20)
            if self.facing() != FACE_RIGHT:
                self.emu.run(120)
                continue
            self.emu.hold("LEFT", 6, 20)
            return self.facing() == FACE_LEFT
        return False

    def player_tile_or_none(self):
        """player_tile, or None while the MapObject chain is torn down
        and rebuilt during a warp (normal for a few frames)."""
        mobj = self._map_object_addr()
        if mobj is None:
            return None
        try:
            x, y, z = struct.unpack("<iii", self.emu.read(mobj + 100, 12))
        except Exception:
            return None
        # y == 0 (and (0,0,0)) is the transient mid-warp garbage, not
        # a real tile: floor is y 1, walls 2+, ceiling 10, stairs 2.
        if not (-64 <= x <= 160 and 1 <= y <= 32 and -64 <= z <= 160):
            return None
        return (x, y // 2, z)

    def current_map(self):
        """Map header id from FieldSystem.location (a pointer at +0x1C;
        the Location's mapId is its first word). -1 while the chain is
        torn down during a warp."""
        try:
            fs = self._read32(self.syms["sFieldSystem"][0])
            if not _in_ram(fs):
                return -1
            loc = self._read32(fs + 0x1C)
            if not _in_ram(loc):
                return -1
            return self._read32(loc)
        except Exception:
            return -1

    def surface(self):
        """DwPuzzleSurface for the player's tile (debug struct first,
        tile inference fallback). During a warp the tile is briefly
        unreadable; the last known surface is returned then."""
        dbg = self.debug()
        if dbg is not None and dbg["active"] and dbg["mapHeader"] == self.rift.map_id:
            self._last_surface = dbg["surface"]
            return dbg["surface"]
        t = self.player_tile_or_none()
        if t is None:
            return getattr(self, "_last_surface", SURF_FLOOR)
        x, y, _z = t
        if y == 1:
            surf = SURF_FLOOR
        elif y == 10:
            surf = SURF_CEIL
        elif self.rift is not None and self.rift.wall_x is not None and x == self.rift.wall_x:
            surf = self.rift.wall_side
        else:
            surf = SURF_WEST if x <= 25 else SURF_EAST
        self._last_surface = surf
        return surf

    def debug(self):
        """gDwPuzzleDebug (engine-a) as a dict, or None when the symbol
        is absent. Sanity-checked; a struct that fails the checks is
        treated as absent, never trusted."""
        if "gDwPuzzleDebug" not in self.syms:
            return None
        if self._debug_addr is None:
            self._debug_addr = self.syms["gDwPuzzleDebug"][0]
        # The struct grows as engine-a/b add fields (rift-213 needs
        # stoneStates[]). Read the symbol's full xMAP size when known
        # (at least 172), and parse the tail tolerantly below.
        debug_size = max(172, self.syms["gDwPuzzleDebug"][1])
        raw = self.emu.read(self._debug_addr, debug_size)
        # Explicit offsets (dw_puzzle.h DwPuzzleDebug), not one format
        # string, so a layout drift fails on a named field, not a size.
        map_header, active = struct.unpack_from("<II", raw, 0)
        px, py, pz = struct.unpack_from("<hhh", raw, 8)
        surf, tile_state = raw[14], raw[15]
        group_bits, group_disp, sigil_bits = struct.unpack_from("<III", raw, 20)
        cp_index = struct.unpack_from("<I", raw, 32)[0]
        cp_x, cp_y, cp_z = struct.unpack_from("<hhh", raw, 36)
        fall_count, frame_count = struct.unpack_from("<II", raw, 44)
        slide_active = struct.unpack_from("<I", raw, 52)[0]
        slide_dir = struct.unpack_from("<b", raw, 56)[0]
        if active not in (0, 1) or surf > 4 or tile_state > 3:
            return None
        if active and map_header not in (0, self.rift.map_id if self.rift else 0):
            return None
        slide_tx, slide_ty, slide_tz = struct.unpack_from("<hhh", raw, 60)
        last_event, last_frame, last_group = struct.unpack_from("<III", raw, 68)
        flash, reset_gen = struct.unpack_from("<II", raw, 80)
        stones = []
        for i in range(8):
            sx, sy, sz, present, _p = struct.unpack("<hhhBB", raw[88 + i * 8:96 + i * 8])
            stones.append({"x": sx, "y": sy, "z": sz, "present": present})
        stone_count, shadow_phase, shx, shy, shz, ex, ey, ez = struct.unpack(
            "<IIhhhhhh", raw[152:172])
        # stoneStates[] (engine-a/b, for rift-213 stones): RESTING 0,
        # FALLING 1, LANDED 2, one per stone. Layout provisional until
        # engine-a lands it: if the symbol is big enough for 8 u32s
        # after the 172-byte prefix, read those; else if there is any
        # tail at all, read it as u8s; else []. The first 172 bytes
        # are always parsed as above, so growth never breaks the
        # reader -- it only adds (possibly empty) stoneStates.
        stone_states = []
        tail = raw[172:]
        if len(tail) >= 32:
            stone_states = list(struct.unpack("<8I", tail[:32]))
        elif tail:
            stone_states = list(tail)
        return {"mapHeader": map_header, "active": active,
                "player": (px, py, pz), "surface": surf, "tileState": tile_state,
                "groupBits": group_bits, "groupDisplayBits": group_disp,
                "sigilBits": sigil_bits, "checkpointIndex": cp_index,
                "checkpoint": (cp_x, cp_y, cp_z), "fallCount": fall_count,
                "frameCount": frame_count, "slideActive": slide_active,
                "slideDir": slide_dir, "slideTarget": (slide_tx, slide_ty, slide_tz),
                "lastEvent": last_event, "lastEventName": EV_NAME.get(last_event, "?"),
                "lastEventFrame": last_frame, "lastEventGroup": last_group,
                "flashFrames": flash, "resetGeneration": reset_gen,
                "stones": stones, "stoneCount": stone_count,
                "stoneStates": stone_states,
                "shadowPhase": shadow_phase, "shadow": (shx, shy, shz),
                "echo": (ex, ey, ez)}

    # -- movement ---------------------------------------------------------

    def wait_settled(self, timeout=300, stable_frames=12):
        """Wait until the player's tile is unchanged for `stable_frames`.
        Returns the tile. A step animation / jump / script move settles
        here; a fall warp also settles, at the respawn tile."""
        last, stable = None, 0
        start = self.emu.frame
        while self.emu.frame - start < timeout:
            t = self.player_tile_or_none()
            if t is None:
                self.emu.run(1)
                continue
            if t == last:
                stable += 1
                if stable >= stable_frames:
                    return t
            else:
                last, stable = t, 0
            self.emu.run(1)
        return self.player_tile_or_none() or last

    def in_overworld(self):
        return self.emu.in_overworld()

    def battle_menu_up(self):
        return self.emu.battle_menu_up()

    def textbox_up(self, img=None):
        """Field message box open? The box sits on the top screen,
        rows 140-175, with a light background. Calibrated: 0.56 with
        a box open, 0.00 without (the DW floor has no such band).
        The Poketch bottom screen stays up during field dialogue, so
        in_overworld() alone cannot detect it."""
        img = img or self.emu.screens()
        tot = white = 0
        for y in range(140, 175):
            for x in range(256):
                r, g, b = img.getpixel((x, y))[:3]
                tot += 1
                if r > 200 and g > 200 and b > 200:
                    white += 1
        return white / tot > 0.25

    def pump_text(self, max_frames=900, tap_every=40):
        """Advance field dialogue with A until no message box is open
        and the overworld is back, or the battle menu appears.
        Returns 'overworld' / 'battle' / 'timeout'. Never taps while
        the battle menu is up. A Yes/No prompt is answered by A (the
        default choice) -- the rift entries rely on that for Eterna
        Forest."""
        start = self.emu.frame
        while self.emu.frame - start < max_frames:
            if self.emu.battle_menu_up():
                return "battle"
            if self.emu.in_overworld() and not self.textbox_up():
                # Scripts chain message -> movement -> message; a
                # clear box for one instant is not the end.
                self.emu.run(120)
                if self.textbox_up():
                    continue
                return "overworld"
            self.emu.tap("A", tap_every)
        if self.emu.battle_menu_up():
            return "battle"
        return "timeout" if self.textbox_up() or not self.emu.in_overworld() else "overworld"

    def step(self, face, advance_text=True, timeout=200):
        """Press one FACE_* direction and wait for the step to finish.
        Returns a dict: moved, fell, tile before/after, surface, event,
        and where the game ended up ('overworld' / 'battle' / 'script').
        Blocked steps return moved=False. Dialogue opened by the step
        (fork lines, ghost acts) is advanced when advance_text is set;
        the totem battle menu stops the pump. INTERACT taps A, WAIT
        runs 60 frames."""
        if face == INTERACT:
            before = self._wait_tile()
            status = self.pump_text() if advance_text else (
                "battle" if self.emu.battle_menu_up() else "overworld")
            return {"move": "A", "face": face, "before": before,
                    "after": self.player_tile_or_none() or before, "surfaceBefore": self.surface(),
                    "surface": self.surface(), "moved": False, "fell": False,
                    "status": status, "debug": self.debug(), "frame": self.emu.frame}
        if face == WAIT:
            before = self._wait_tile()
            self.emu.run(60)
            return {"move": ".", "face": face, "before": before,
                    "after": self.player_tile_or_none() or before, "surfaceBefore": self.surface(),
                    "surface": self.surface(), "moved": False, "fell": False,
                    "status": "overworld" if self.emu.in_overworld() else "script",
                    "debug": self.debug(), "frame": self.emu.frame}
        before = self._wait_tile()
        surf_before = self.surface()
        dbg_before = self.debug()
        falls_before = dbg_before["fallCount"] if dbg_before else None
        changed = self._press_step(face, before, timeout)
        after = self.wait_settled(timeout=600)
        status = "overworld"
        # A step hook's script opens its first message box well after
        # the step settles (the totem script's first line is ~150
        # frames in, after fanfare and movements). Re-check a few
        # times and pump anything that appears; a script with no box
        # (the halfway fly-by) just costs the recheck window.
        for _ in range(3):
            self.emu.run(80)
            if self.emu.battle_menu_up():
                status = "battle"
                break
            if not self.emu.in_overworld() or self.textbox_up():
                if advance_text:
                    status = self.pump_text()
                    continue  # chained message -> movement -> message
                status = "script"
                break
            break
        # Script grace, then settle again: a late warp (fall, fold,
        # carry) must be this step's outcome, not the next step's
        # mystery teleport.
        if advance_text and status != "battle":
            self.emu.run(100)
            after = self.wait_settled(timeout=600)
        # A fall warp (or a checkpoint respawn) settles the player at
        # the entry/checkpoint. It is a fall only when the step did
        # not target that tile itself: walking back onto the entry
        # tile (R from (19,12) to (20,12)) is not a fall, and stepping
        # onto a fall lip next to the entry (D from (20,12) to
        # (20,13)) is one. Fold warps and carries settle elsewhere,
        # so they never match.
        fell = False
        dbg_after = self.debug()
        if dbg_after is not None and falls_before is not None:
            fell = dbg_after["fallCount"] > falls_before
        elif self.rift is not None and after in (
                (self.rift.entry[0], 1, self.rift.entry[1]),
                self.rift.checkpoint_tile):
            delta = DIR_DELTA[surf_before][face]
            target = (before[0] + delta[0], before[1] + delta[1],
                      before[2] + delta[2])
            fell = changed and target != after
        return {"move": FACE_LETTER[face], "face": face, "before": before,
                "after": after, "surfaceBefore": surf_before,
                "surface": self.surface(), "moved": changed or after != before,
                "fell": fell, "status": status,
                "debug": dbg_after, "frame": self.emu.frame}

    def _wait_tile(self, timeout=180):
        """A readable player tile, waiting out a warp's teardown."""
        start = self.emu.frame
        while self.emu.frame - start < timeout:
            t = self.player_tile_or_none()
            if t is not None:
                return t
            self.emu.run(1)
        raise RuntimeError("player tile unreadable (bad MapObject chain)")

    def _press_step(self, face, before, timeout):
        """Press a direction until the tile changes. Returns True if
        the tile changed (a step, a jump, or a scripted move)."""
        self.emu.press(FACE_KEY[face])
        changed = False
        start = self.emu.frame
        while self.emu.frame - start < timeout:
            self.emu.run(1)
            t = self.player_tile_or_none()
            if t is not None and t != before:
                changed = True
                break
        self.emu.release(FACE_KEY[face])
        return changed

    def replay(self, moves, advance_text=True, frames_out=None, label="replay",
               stop=None):
        """Replay a move list (string or [FACE_*]). Returns the trace
        (one dict per step, as step() returns). `stop` is an optional
        predicate(trace_so_far) -> True to halt early. With frames_out,
        a frame is snapped after every step for a strip."""
        moves = parse_moves(moves) if isinstance(moves, str) else list(moves)
        trace = []
        for face in moves:
            st = self.step(face, advance_text=advance_text)
            trace.append(st)
            if frames_out is not None:
                tag = "A" if face == INTERACT else ("." if face == WAIT else FACE_LETTER[face])
                self.emu.snap(f"{label}-{tag}", frames_out)
            if stop is not None and stop(trace):
                break
        return trace

    # -- events ------------------------------------------------------------

    def wait_for(self, pred, timeout=1800, step_frames=5, label="wait"):
        """wait_until with the DwSession signature (pred takes self)."""
        return self.emu.wait_until(lambda _e: pred(self), timeout=timeout,
                                   step=step_frames, label=label)

    def fall_count(self):
        dbg = self.debug()
        return dbg["fallCount"] if dbg else None

    # -- strips -------------------------------------------------------------

    def strip(self, frames, path, title="", cols=8, scale=0.5):
        """Deduplicated, labelled contact sheet from Frame list."""
        frames = dedupe(frames)
        return contact_sheet(frames, str(path), title, cols=cols, scale=scale)
