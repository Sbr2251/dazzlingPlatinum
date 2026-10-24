// Debug-only puzzle table for MAP_HEADER_DW_ETERNA_FOREST (engine-a).
//
// Exercises every engine module, behind test mode only (testOnly = 1).
// Enter through the real Eterna rift (progress 23 -> 24). It does not
// touch the honeycomb tiles (44-45, 33-36) as engine tiles (they are
// not in the table): the stock honeycomb fall still owns them, and the
// glue calls DwPuzzle_NotifyFall on both honeycomb fall paths (frame
// hook + step hook) so the fall restores the checkpoint snapshot.
//
// Landing rule (rift-ef): a landing fires NOTHING (a jump, warp or
// respawn landing never calls the step hook). So every checkpoint and
// sigil below sits on a WALKED tile, never on a landing tile:
//   - the fold warps to (40,22), so checkpoint 1 is (41,22) (walked to
//     right after the fold), not (40,22);
//   - the stock wall jump lands at (49,1,21), so checkpoint 2 is
//     (49,2,21) (the first climb step), not (49,1,21);
//   - the ceiling is reached by a jump to (49,10,27), so checkpoint 3
//     is (49,10,28) (walked to on the way back from the bridge).
// The route (grids from tools/distortion_world/twarc.py dump 597):
//   entry (20,1,12) checkpoint 0; walk to the fold (17,12) -> hive (40,1,22).
//   (40,1,22) is the RESET sigil (restores the checkpoint-1 snapshot).
//   east along the hive strip: (42,1,22) TOGGLE sigil for group 0;
//     (44-47,1,22) CURRENT, drift +x, slide to the landing (48,1,22).
//   (39,1,22) is an explicit VOID on the ground (rift-213 (2)): the
//     player must be able to step onto it even when the stock terrain
//     collision bit is set (the glue overrides it), then fall. With a
//     LANDED stone's SOLID actor tile there, the player walks on it.
//   press RIGHT at (48,1,22): the stock jump onto the east wall (49,1,21);
//     climb: UP to (49,2,21) checkpoint 2, UP, RIGHT x3, UP x3, RIGHT x3,
//     to (49,5,27).
//   (49,5,27) is a RUNE: wall -> ceiling, landing (47,10,30), rot -90
//     (the stock wall->ceiling rotation). (47,10,30) carries a TOGGLE
//     sigil for group 0: the rune landing must NOT fire it (landing rule);
//     group 0 stays ON after the landing.
//   On the ceiling: group 0's bridge tiles (49,10,30), (49,10,31) are
//     BLOCKED while group 0 is off (bump), SOLID once toggled on.
//   (49,10,28) is a MOMENTARY sigil for group 1 (group 1's tile
//     (46,10,29), off the walked path, is BLOCKED unless the sigil is
//     stood on -- a momentary-held tile the player must step on would
//     be unreachable, so the hold is observed in gDwPuzzleDebug).
//   (49,10,32) is a TOGGLE sigil for group 0, stepped on after
//     checkpoint 3 on the way to the honeycomb: it turns group 0 OFF, so
//     a honeycomb fall after it proves the restore puts group 0 back ON.
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
    // Landing rule: on the rune's landing tile. Must NOT fire on the landing.
    { 47, 10, 30, DW_PUZZLE_SIGIL_TOGGLE, 0, 0, DW_PUZZLE_SURFACE_CEILING },
    // Honeycomb restore: toggles group 0 OFF after checkpoint 3, so a
    // honeycomb fall proves the restore puts it back ON.
    { 49, 10, 32, DW_PUZZLE_SIGIL_TOGGLE, 0, 0, DW_PUZZLE_SURFACE_CEILING },
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

// Checkpoints sit on WALKED tiles only (landing rule): the fold warps to
// (40,22), the wall jump lands at (49,1,21), the ceiling jump lands at
// (49,10,27) -- none of those fires a checkpoint.
static const DwPuzzleCheckpoint sTestCheckpoints[] = {
    { 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
    { 41, 1, 22, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
    { 49, 2, 21, -1, DW_PUZZLE_SURFACE_EAST_WALL, { 0, 0 } },
    { 49, 10, 28, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
};

static const DwPuzzleTile sTestTiles[] = {
    { 46, 10, 28, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_CEILING, 5, 0 },
    // GROUND explicit VOID (rift-213 (2)): the glue must let the player
    // step onto it even when the stock terrain collision bit is set.
    { 39, 1, 22, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 5, 0 },
};

const DwPuzzleTable gDwPuzzleTestEternaTable = {
    MAP_HEADER_DW_ETERNA_FOREST,
    0, 0,                       // any VAR_ARC2_PROGRESS
    5, VAR_MAP_LOCAL_2,         // frame-fall script (HoneyFall), fallVar
    2, 5, 1, 4, 4, 2,           // group/sigil/rune/current/checkpoint/tile counts
    1, 0,                       // testOnly, padding
    sTestGroups, sTestSigils, sTestRunes, sTestCurrents, sTestCheckpoints, sTestTiles,
};
