// Debug-only puzzle table for MAP_HEADER_DW_ETERNA_FOREST (engine-a).
//
// Exercises every engine module, behind test mode only (testOnly = 1).
// Enter through the real Eterna rift (progress 23 -> 24). It does not
// touch the honeycomb (ghost-prop group 1, owned by the stock Eterna
// timer/frame hook): the honeycomb tiles (44-45, 33-36) are not engine
// tiles, so the stock honeycomb fall still owns them.
//
// The route (grids from tools/distortion_world/twarc.py dump 597):
//   entry (20,1,12) checkpoint 0; walk to the fold (17,12) -> hive (40,1,22)
//     checkpoint 1 (the fold is a coord event, not an engine trigger).
//   (40,1,22) is the RESET sigil (restores the checkpoint-1 snapshot).
//   east along the hive strip: (42,1,22) TOGGLE sigil for group 0;
//     (44-47,1,22) CURRENT, drift +x, slide to the landing (48,1,22).
//   press RIGHT at (48,1,22): the stock jump onto the east wall (49,1,21)
//     checkpoint 2. Climb the wall: UP x2, RIGHT x3, UP x3, RIGHT x3,
//     UP x3 to (49,9,27) (the wall steps, attr 17).
//   (49,5,27) is a RUNE: wall -> ceiling, landing (47,10,30), rot -90
//     (the stock wall->ceiling rotation). The stock climb reaches the
//     ceiling at (49,10,27) checkpoint 3 instead.
//   On the ceiling: group 0's bridge tiles (49,10,30), (49,10,31) are
//     BLOCKED while group 0 is off (bump), SOLID once toggled on
//     (the rune lands at (47,10,30), past the bridge).
//   (49,10,28) is a MOMENTARY sigil for group 1 (group 1's tile
//     (46,10,29), off the walked path, is BLOCKED unless the sigil is
//     stood on -- a momentary-held tile the player must step on would
//     be unreachable, so the hold is observed in gDwPuzzleDebug).
//   (46,10,28) is VOID: a fall, and the engine respawns the player at
//     the last checkpoint with the checkpoint snapshot restored.
//     Step falls use the HoneyFall script (entry 5), which clears
//     VAR_MAP_LOCAL_2 and warps to the hive; the engine respawn then
//     moves the player to the checkpoint. The table's frame-fall
//     script is the same 5.

#include "generated/map_headers.h"
#include "generated/vars_flags.h"

#include "location.h"
#include "overlay009/dw_puzzle.h"

static const DwPuzzleTile sTestGroup0Tiles[] = {
    { 49, 10, 30, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 49, 10, 31, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
};

static const DwPuzzleTile sTestGroup1Tiles[] = {
    { 46, 10, 29, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
};

static const DwPuzzleGroup sTestGroups[] = {
    { sTestGroup0Tiles, 2, 0, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
    { sTestGroup1Tiles, 1, DW_PUZZLE_GHOST_GROUP_NONE, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
};

static const DwPuzzleSigil sTestSigils[] = {
    { 42, 1, 22, DW_PUZZLE_SIGIL_TOGGLE, 0, 0, DW_PUZZLE_SURFACE_GROUND },
    { 49, 10, 28, DW_PUZZLE_SIGIL_MOMENTARY, 1, 0, DW_PUZZLE_SURFACE_CEILING },
    { 40, 1, 22, DW_PUZZLE_SIGIL_RESET, 0, 0, DW_PUZZLE_SURFACE_GROUND },
};

static const DwPuzzleRune sTestRunes[] = {
    // East wall (49,5,27) -> ceiling (47,10,30). steps 0 = 16, no camera
    // (the stock camera templates at the ceiling take over).
    { 49, 5, 27, 47, 10, 30, DW_PUZZLE_SURFACE_EAST_WALL, DW_PUZZLE_SURFACE_CEILING,
      -1, 0, -90, 0, 0, 0, 0, 0, 0 },
};

static const DwPuzzleCurrent sTestCurrents[] = {
    { 44, 1, 22, FACE_RIGHT, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
    { 45, 1, 22, FACE_RIGHT, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
    { 46, 1, 22, FACE_RIGHT, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
    { 47, 1, 22, FACE_RIGHT, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
};

static const DwPuzzleCheckpoint sTestCheckpoints[] = {
    { 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
    { 40, 1, 22, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
    { 49, 1, 21, -1, DW_PUZZLE_SURFACE_EAST_WALL, { 0, 0 } },
    { 49, 10, 27, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
};

static const DwPuzzleTile sTestTiles[] = {
    { 46, 10, 28, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_CEILING, 5, 0 },
};

const DwPuzzleTable gDwPuzzleTestEternaTable = {
    MAP_HEADER_DW_ETERNA_FOREST,
    0, 0,                       // any VAR_ARC2_PROGRESS
    5, VAR_MAP_LOCAL_2,         // frame-fall script (HoneyFall), fallVar
    2, 3, 1, 4, 4, 1,           // group/sigil/rune/current/checkpoint/tile counts
    1, 0,                       // testOnly, padding
    sTestGroups, sTestSigils, sTestRunes, sTestCurrents, sTestCheckpoints, sTestTiles,
};
