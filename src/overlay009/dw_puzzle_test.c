// Debug-only puzzle table for MAP_HEADER_DW_RAVAGED_PATH (engine-a).
//
// Exercises every engine module, behind test mode only (testOnly = 1):
// the table is returned only while gDwPuzzleTestMode is on. With test
// mode off, Ravaged Path has no table and plays exactly as today.
//
// The route (all tiles are stock-walkable; see tools/distortion_world/
// ravaged_path.json for the wall grid):
//   entry (20,1,12) checkpoint 0; step on the entry tile again for the
//     RESET sigil (restores the checkpoint-0 snapshot).
//   walk to the ledge (12,1,14), step on the TOGGLE sigil: group 0 on.
//   jump onto the wall (11,2,13) checkpoint 1.
//   (11,2,15), (11,2,17), (11,2,18) are group-0 bridge tiles: BLOCKED
//     while group 0 is off (the player bumps), SOLID once toggled on.
//     Group 0's ghost-prop group is tw_arc group 0 (decor), so toggling
//     exercises the honeycomb fade: props fade out over 33 frames while
//     the tiles stay solid, props show 3 frames before the tiles hold.
//   (11,2,18) is a CURRENT (drift +z): a slide carries the player to
//     the fork tile (11,2,19) and ends there. (The Ravaged fork line may
//     play on the landing; it plays once.)
//   back to (11,2,19), up to (11,4,19): MOMENTARY sigil for group 1
//     (group 1's tile (11,4,21) is BLOCKED unless the sigil is stood on;
//     debug groupBits shows group 1 on while stood on, off after).
//   (11,4,20) is a RUNE: wall -> base ground, landing (12,1,23)
//     checkpoint 2, facing south.
//   (13,1,23) is a CURRENT (drift -x): a slide carries the player back
//     to the checkpoint tile (12,1,23) and ends there.
//   VOID test: from (11,2,13), step UP to (11,3,13): a fall, and the
//     engine respawns the player at the last checkpoint with the
//     checkpoint snapshot restored (group 0 back to the state it had
//     when the checkpoint was reached).
//
// The Ravaged scar logic still runs underneath (its hook runs after the
// engine in the per-map step hook): the route avoids re-stepping a scar.
// The fall script is the map's existing DWRavagedPath_Fall (entry 2),
// which clears VAR_MAP_LOCAL_3 (the frame-fall var).

#include "generated/map_headers.h"
#include "generated/vars_flags.h"

#include "location.h"
#include "overlay009/dw_puzzle.h"

static const DwPuzzleTile sTestGroup0Tiles[] = {
    { 11, 2, 15, 0, DW_PUZZLE_SURFACE_WEST_WALL, 0, 0 },
    { 11, 2, 17, 0, DW_PUZZLE_SURFACE_WEST_WALL, 0, 0 },
    { 11, 2, 18, 0, DW_PUZZLE_SURFACE_WEST_WALL, 0, 0 },
};

static const DwPuzzleTile sTestGroup1Tiles[] = {
    { 11, 4, 21, 0, DW_PUZZLE_SURFACE_WEST_WALL, 0, 0 },
};

static const DwPuzzleGroup sTestGroups[] = {
    // Bridge: ghost-prop group 0 (tw_arc decor) for the fade exercise.
    { sTestGroup0Tiles, 3, 0, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
    // Momentary-held tile: no props, switches at once.
    { sTestGroup1Tiles, 1, DW_PUZZLE_GHOST_GROUP_NONE, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_BLOCKED, 0, 0 },
};

static const DwPuzzleSigil sTestSigils[] = {
    { 12, 1, 14, DW_PUZZLE_SIGIL_TOGGLE, 0, 0, DW_PUZZLE_SURFACE_GROUND },
    { 11, 4, 19, DW_PUZZLE_SIGIL_MOMENTARY, 1, 0, DW_PUZZLE_SURFACE_WEST_WALL },
    { 20, 1, 12, DW_PUZZLE_SIGIL_RESET, 0, 0, DW_PUZZLE_SURFACE_GROUND },
};

static const DwPuzzleRune sTestRunes[] = {
    // Wall (11,4,20) -> base ground (12,1,23). steps/cameraSteps 0 = 16.
    { 11, 4, 20, 12, 1, 23, DW_PUZZLE_SURFACE_WEST_WALL, DW_PUZZLE_SURFACE_GROUND,
      FACE_DOWN, 0, 90, 0, 1, 0, 0, 0, 0 },
};

static const DwPuzzleCurrent sTestCurrents[] = {
    { 11, 2, 18, FACE_LEFT, DW_PUZZLE_SURFACE_WEST_WALL, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
    { 13, 1, 23, FACE_LEFT, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
};

static const DwPuzzleCheckpoint sTestCheckpoints[] = {
    { 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
    { 11, 2, 13, -1, DW_PUZZLE_SURFACE_WEST_WALL, { 0, 0 } },
    { 12, 1, 23, FACE_DOWN, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
};

static const DwPuzzleTile sTestTiles[] = {
    { 11, 3, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_WEST_WALL, 2, 0 },
};

const DwPuzzleTable gDwPuzzleTestTable = {
    MAP_HEADER_DW_RAVAGED_PATH,
    0, 0,               // any VAR_ARC2_PROGRESS
    2, VAR_MAP_LOCAL_3, // fallScriptId (DWRavagedPath_Fall), fallVar
    2, 3, 1, 2, 3, 1,   // group/sigil/rune/current/checkpoint/tile counts
    1, 0,               // testOnly, padding
    sTestGroups, sTestSigils, sTestRunes, sTestCurrents, sTestCheckpoints, sTestTiles,
};
