// Production puzzle table for MAP_HEADER_DW_RAVAGED_PATH (rift-rp, Phase 2).
//
// Design: docs/distortion_world/ravaged_path.md. One SET sigil on the west
// wall at (11, 2, 14) switches bridge group 0 ON (it never switches it off,
// so the fade-out path is never exercised in this rift). Group 0's three
// bridge tiles are SOLID while on, BLOCKED while off. The crumbling scars
// are NOT in this table: the existing per-map scar hook in ov9_02249960.c
// (Arc2DwRavagedPath_HandleStep) owns them, and it calls
// DwPuzzle_NotifyFall() before starting the fall script, so a scar fall
// restores the checkpoint snapshot exactly like a lip fall.
//
// Surfaces are explicit (engine-a v2): the floor is GROUND (base map
// terrain), the wall is WEST_WALL. The chasm lips are explicit VOID
// overrides with fallScriptId 2 (DWRavagedPath_Fall), so a lip fall is
// seen by the engine step hook and restores the snapshot. The table's
// fallScriptId / fallVar are the frame-fall pair (engine-a added the
// init-table line and the VAR_MAP_LOCAL_3 clear to the map's scripts);
// this rift has no frame-detected fall, but the pair must be wired so a
// fall the frame hook ever reports starts the right script.

#include "generated/map_headers.h"
#include "generated/vars_flags.h"

#include "location.h"
#include "overlay009/dw_puzzle.h"

static const DwPuzzleTile sRavagedPathBridgeTiles[] = {
    { 11, 2, 15, 0, DW_PUZZLE_SURFACE_WEST_WALL, 0, 0 },
    { 11, 4, 20, 0, DW_PUZZLE_SURFACE_WEST_WALL, 0, 0 },
    { 11, 4, 21, 0, DW_PUZZLE_SURFACE_WEST_WALL, 0, 0 },
};

static const DwPuzzleGroup sRavagedPathGroups[] = {
    // Bridges: ghost-prop group 4 (tw_arc, see tools/distortion_world/
    // ravaged_path.json); fade timings 0 = engine defaults (33 out, 3 in).
    { sRavagedPathBridgeTiles, 3, 4, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
};

static const DwPuzzleSigil sRavagedPathSigils[] = {
    { 11, 2, 14, DW_PUZZLE_SIGIL_SET, 0, 1, DW_PUZZLE_SURFACE_WEST_WALL },
};

static const DwPuzzleCheckpoint sRavagedPathCheckpoints[] = {
    { 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
};

// Chasm lips (coord events in events_dw_ravaged_path.json): step = fall.
static const DwPuzzleTile sRavagedPathTiles[] = {
    { 15, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 19, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 20, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 21, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 20, 1, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 21, 1, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 12, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 13, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 14, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 15, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
};

const DwPuzzleTable gDwPuzzleRavagedPathTable = {
    MAP_HEADER_DW_RAVAGED_PATH,
    14, 14,               // VAR_ARC2_PROGRESS gate: this scene only
    2, VAR_MAP_LOCAL_3,   // fallScriptId (DWRavagedPath_Fall), fallVar (frame fall)
    1, 1, 0, 0, 1, 10,    // group/sigil/rune/current/checkpoint/tile counts
    0, 0,                 // testOnly (production), padding
    sRavagedPathGroups, sRavagedPathSigils, NULL, NULL, sRavagedPathCheckpoints, sRavagedPathTiles,
};
