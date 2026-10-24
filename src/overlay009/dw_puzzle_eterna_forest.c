// Puzzle table for MAP_HEADER_DW_ETERNA_FOREST (rift-ef, scene 2.10).
// Design: docs/distortion_world/eterna_forest.md (difficulty 3,
// gravity runes + honeycomb timing, one SET sigil, 25-40 steps).
//
// Surfaces (dw_puzzle.h v2): base-map terrain is GROUND (4), not FLOOR
// (0, a floating floor platform). The entry walkway, the hive strip and
// the Rune B platform are base terrain, so every entry below that sits
// on them uses GROUND. The wall is EAST_WALL, the ceiling is CEILING.
//
// Landing rule: a landing fires NOTHING, so every sigil and checkpoint
// below sits on a WALKED tile, never on a landing tile:
//   - the fold warps to (40,22), so there is no checkpoint there;
//   - the stock wall jump lands at (49,1,21), so there is no checkpoint there;
//   - the Rune B flip lands at (45,1,37), so the sigil is at (46,1,37),
//     reached by a walked step east after the flip; the flip back up
//     fires on the walked step west onto (45,1,37).
// The honeycomb (44-45, 33-36) is NOT an engine group: the stock timer
// owns it, and the glue calls DwPuzzle_NotifyFall on both honeycomb
// fall paths (frame hook + step hook) so a honeycomb fall restores
// the checkpoint snapshot. The entry-chasm lips ARE engine VOID
// tiles (fallScriptId 2, their own script); their coord events were
// removed from events_dw_eterna_forest.json so the fall goes through
// the engine exactly once.

#include "generated/map_headers.h"
#include "generated/vars_flags.h"

#include "location.h"
#include "overlay009/dw_puzzle.h"

// Bridge group: the gap (44..47, 10, 39..40), BLOCKED until the sigil
// latches it ON. Fade fields 0 -> defaults (fadeOut 33, fadeInLead 3).
static const DwPuzzleTile sBridgeTiles[] = {
    { 44, 10, 39, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 45, 10, 39, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 46, 10, 39, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 47, 10, 39, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 44, 10, 40, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 45, 10, 40, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 46, 10, 40, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 47, 10, 40, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
};

static const DwPuzzleGroup sGroups[] = {
    { sBridgeTiles, 8, 2, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
};

// The one sigil: SET the bridge ON, on the EAST platform tile (walked step).
static const DwPuzzleSigil sSigils[] = {
    { 46, 1, 37, DW_PUZZLE_SIGIL_SET, 0, 1, DW_PUZZLE_SURFACE_GROUND },
};

// Gravity runes, one entry per direction. rot/steps copy the stock
// wall<->ceiling jumps (wall -> ceiling -90, ceiling -> wall 90);
// Rune B is 180 both ways (upside-down <-> upright). steps 0 = 16,
// useCamera 0 (the stock camera templates at the destination take over).
static const DwPuzzleRune sRunes[] = {
    { 49, 1, 25, 49, 10, 25, DW_PUZZLE_SURFACE_EAST_WALL, DW_PUZZLE_SURFACE_CEILING,
      -1, 0, -90, 0, 0, 0, 0, 0, 0 },
    { 49, 10, 25, 49, 1, 25, DW_PUZZLE_SURFACE_CEILING, DW_PUZZLE_SURFACE_EAST_WALL,
      -1, 0, 90, 0, 0, 0, 0, 0, 0 },
    { 45, 10, 37, 45, 1, 37, DW_PUZZLE_SURFACE_CEILING, DW_PUZZLE_SURFACE_GROUND,
      -1, 0, 180, 0, 0, 0, 0, 0, 0 },
    { 45, 1, 37, 45, 10, 37, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_SURFACE_CEILING,
      -1, 0, 180, 0, 0, 0, 0, 0, 0 },
};

// Checkpoints, all on guaranteed WALKED, non-rune tiles: entry;
// honeycomb approach (44/45, 32); bridge z=39 (every crossing steps
// on one). Snapshots: approach = bridge as on arrival (OFF first
// time); bridge = always ON by construction.
static const DwPuzzleCheckpoint sCheckpoints[] = {
    { 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
    { 44, 10, 32, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
    { 45, 10, 32, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
    { 44, 10, 39, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
    { 45, 10, 39, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
    { 46, 10, 39, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
    { 47, 10, 39, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
};

static const DwPuzzleTile sTiles[] = {
    // Rune B platform (stock base terrain is blocked there).
    { 45, 1, 37, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 46, 1, 37, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    // Entry-walkway chasm lips: VOID, fall script 2 (DWEternaForest_Fall).
    { 15, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 19, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 20, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 21, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 20, 1, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 21, 1, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
};

const DwPuzzleTable gDwPuzzleEternaForestTable = {
    MAP_HEADER_DW_ETERNA_FOREST,
    24, 24,                      // VAR_ARC2_PROGRESS gate
    5, VAR_MAP_LOCAL_2,           // frame-fall script (HoneyFall), fallVar
    1, 1, 4, 0, 7, 8,            // group/sigil/rune/current/checkpoint/tile counts
    0, 0,                        // testOnly (production table), padding
    sGroups, sSigils, sRunes, NULL, sCheckpoints, sTiles,
};
